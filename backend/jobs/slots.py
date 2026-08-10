"""Concurrency slots for research jobs (Redis lease + PG reconciliation).

- Per user: max 1 active report job
- Global: max 2 active jobs (aligns with ARQ_MAX_JOBS)
- Lease TTL prevents permanent lock after crashes; leak reaper cleans orphans
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = frozenset(
    {
        "pending_dispatch",
        "queued",
        "running",
        "retrying",
        "stale",
        "cancel_requested",
        "cancelling",
    }
)


def _env_int(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def max_concurrent_per_user() -> int:
    return _env_int("RESEARCH_MAX_CONCURRENT_PER_USER", 1)


def max_concurrent_global() -> int:
    return _env_int("RESEARCH_MAX_CONCURRENT_GLOBAL", 2)


def max_queue_depth() -> int:
    return _env_int("RESEARCH_MAX_QUEUE_DEPTH", 2)


def slot_lease_sec() -> int:
    timeout = _env_int("RESEARCH_JOB_TIMEOUT_SEC", 1800)
    return _env_int("RESEARCH_SLOT_LEASE_SEC", timeout + 300)


def retry_after_sec() -> int:
    return _env_int("RESEARCH_LIMIT_RETRY_AFTER_SEC", 60)


def _user_key(tenant_id: str, user_id: str) -> str:
    return f"gptr:slots:user:{tenant_id}:{user_id}"


def _global_key() -> str:
    return "gptr:slots:global:active"


def _lease_key(job_id: str) -> str:
    return f"gptr:slot:lease:{job_id}"


@dataclass
class SlotReject:
    code: str
    message: str
    retry_after: int


class SlotAcquireError(Exception):
    def __init__(self, reject: SlotReject):
        self.reject = reject
        super().__init__(reject.message)


_ACQUIRE_LUA = """
local user_key = KEYS[1]
local global_key = KEYS[2]
local lease_key = KEYS[3]
local job_id = ARGV[1]
local user_max = tonumber(ARGV[2])
local global_max = tonumber(ARGV[3])
local lease_ttl = tonumber(ARGV[4])

if redis.call('SISMEMBER', user_key, job_id) == 1 or redis.call('SISMEMBER', global_key, job_id) == 1 then
  redis.call('SADD', user_key, job_id)
  redis.call('SADD', global_key, job_id)
  redis.call('SET', lease_key, job_id, 'EX', lease_ttl)
  return {1, 'ok'}
end

local user_n = redis.call('SCARD', user_key)
if user_max > 0 and user_n >= user_max then
  return {0, 'user_concurrency_limit'}
end
local global_n = redis.call('SCARD', global_key)
if global_max > 0 and global_n >= global_max then
  return {0, 'global_concurrency_limit'}
end
redis.call('SADD', user_key, job_id)
redis.call('SADD', global_key, job_id)
redis.call('SET', lease_key, job_id, 'EX', lease_ttl)
return {1, 'ok'}
"""

_RELEASE_LUA = """
local user_key = KEYS[1]
local global_key = KEYS[2]
local lease_key = KEYS[3]
local job_id = ARGV[1]
redis.call('SREM', user_key, job_id)
redis.call('SREM', global_key, job_id)
redis.call('DEL', lease_key)
return 1
"""


async def _redis():
    from jobs.redis_pool import get_redis

    return await get_redis()


async def count_active_jobs_pg(
    *,
    tenant_id: str | None = None,
    user_id: str | None = None,
) -> int:
    """Authoritative active-job count from PostgreSQL."""
    try:
        from db.session import get_session_factory, is_db_enabled
        from db.models import ResearchJob
        from sqlalchemy import func, select

        if not is_db_enabled():
            return 0
        factory = get_session_factory()
        if factory is None:
            return 0
        async with factory() as session:
            stmt = select(func.count()).select_from(ResearchJob).where(
                ResearchJob.status.in_(tuple(ACTIVE_STATUSES))
            )
            if tenant_id is not None:
                stmt = stmt.where(ResearchJob.tenant_id == tenant_id)
            if user_id is not None:
                stmt = stmt.where(ResearchJob.user_id == user_id)
            return int((await session.execute(stmt)).scalar() or 0)
    except Exception as exc:
        logger.warning("PG active job count failed: %s", exc)
        return 0


async def precheck_capacity(*, tenant_id: str, user_id: str) -> Optional[SlotReject]:
    """Cheap pre-create gate using PG counts (Redis acquire is final)."""
    user_max = max_concurrent_per_user()
    global_max = max_concurrent_global()
    queue_max = max_queue_depth()
    retry = retry_after_sec()

    user_n = await count_active_jobs_pg(tenant_id=tenant_id, user_id=user_id)
    if user_max > 0 and user_n >= user_max:
        return SlotReject(
            code="user_concurrency_limit",
            message="你已有进行中的研究任务，请等待完成或取消后再试",
            retry_after=retry,
        )

    global_n = await count_active_jobs_pg()
    if global_max > 0 and global_n >= global_max:
        return SlotReject(
            code="global_concurrency_limit",
            message="系统并发已满，请稍后再试",
            retry_after=retry,
        )

    # Queue depth ≈ active non-running; for simplicity use global active vs queue max
    if queue_max > 0 and global_n >= queue_max:
        return SlotReject(
            code="queue_full",
            message="队列已满，请稍后再试",
            retry_after=retry,
        )
    return None


async def acquire_slots(*, tenant_id: str, user_id: str, job_id: str) -> None:
    """
    Atomically acquire user+global Redis slots for an already-created job.

    Call ``precheck_capacity`` BEFORE create_job. This function is the Redis
    lease bind; on race it may still reject and the caller must fail the job.
    """
    redis = await _redis()
    if redis is None:
        logger.warning("Redis unavailable — slot lease skipped for job %s", job_id)
        return

    user_max = max_concurrent_per_user()
    global_max = max_concurrent_global()
    lease = slot_lease_sec()
    try:
        result = await redis.eval(
            _ACQUIRE_LUA,
            3,
            _user_key(tenant_id, user_id),
            _global_key(),
            _lease_key(job_id),
            job_id,
            str(user_max),
            str(global_max),
            str(lease),
        )
        ok = int(result[0]) if result else 0
        code = str(result[1]) if result and len(result) > 1 else "unknown"
        if ok == 1:
            return
        messages = {
            "user_concurrency_limit": "你已有进行中的研究任务，请等待完成或取消后再试",
            "global_concurrency_limit": "系统并发已满，请稍后再试",
        }
        raise SlotAcquireError(
            SlotReject(
                code=code,
                message=messages.get(code, "并发名额不足，请稍后再试"),
                retry_after=retry_after_sec(),
            )
        )
    except SlotAcquireError:
        raise
    except Exception as exc:
        logger.warning("Redis slot acquire failed for %s: %s — relying on PG gate", job_id, exc)


async def release_slots(
    *,
    job_id: str,
    tenant_id: str,
    user_id: str,
) -> None:
    redis = await _redis()
    if redis is None:
        return
    try:
        await redis.eval(
            _RELEASE_LUA,
            3,
            _user_key(tenant_id, user_id),
            _global_key(),
            _lease_key(job_id),
            job_id,
        )
    except Exception as exc:
        logger.warning("Redis slot release failed for %s: %s", job_id, exc)


async def refresh_slot_lease(job_id: str) -> None:
    redis = await _redis()
    if redis is None:
        return
    try:
        await redis.expire(_lease_key(job_id), slot_lease_sec())
    except Exception as exc:
        logger.debug("lease refresh failed for %s: %s", job_id, exc)


async def reap_leaked_slots(limit: int = 50) -> int:
    """
    Release Redis slots whose jobs are terminal / missing in PG, or lease expired
    while PG says not active.
    """
    redis = await _redis()
    if redis is None:
        return 0

    released = 0
    try:
        members = await redis.smembers(_global_key())
    except Exception as exc:
        logger.warning("slot leak scan failed: %s", exc)
        return 0

    from jobs import get_job

    for raw in list(members or [])[:limit]:
        job_id = raw.decode() if isinstance(raw, (bytes, bytearray)) else str(raw)
        try:
            job = await get_job(job_id)
            lease_ttl = await redis.ttl(_lease_key(job_id))
            if job is None or job.get("status") not in ACTIVE_STATUSES:
                tid = (job or {}).get("tenant_id") or "anonymous"
                uid = (job or {}).get("user_id") or "anonymous"
                await release_slots(job_id=job_id, tenant_id=tid, user_id=uid)
                released += 1
            elif lease_ttl is not None and int(lease_ttl) == -2:
                # Active in PG but lease gone — renew, do not free the slot
                await redis.set(_lease_key(job_id), job_id, ex=slot_lease_sec())
        except Exception as exc:
            logger.debug("slot leak check %s: %s", job_id, exc)

    # Rebuild Redis from PG if Redis empty after restart but PG has active jobs
    try:
        global_n = await redis.scard(_global_key())
        if global_n == 0:
            await _rebuild_slots_from_pg(redis)
    except Exception as exc:
        logger.debug("slot rebuild skipped: %s", exc)

    if released:
        logger.warning("Released %s leaked research job slot(s)", released)
    return released


async def _rebuild_slots_from_pg(redis) -> int:
    """After Redis flush/restart, rehydrate SETs from PostgreSQL active jobs."""
    try:
        from db.session import get_session_factory, is_db_enabled
        from db.models import ResearchJob
        from sqlalchemy import select

        if not is_db_enabled():
            return 0
        factory = get_session_factory()
        if factory is None:
            return 0
        restored = 0
        async with factory() as session:
            rows = (
                await session.execute(
                    select(ResearchJob).where(ResearchJob.status.in_(tuple(ACTIVE_STATUSES)))
                )
            ).scalars().all()
            for job in rows:
                await redis.sadd(_user_key(job.tenant_id, job.user_id), job.id)
                await redis.sadd(_global_key(), job.id)
                await redis.set(_lease_key(job.id), job.id, ex=slot_lease_sec())
                restored += 1
        if restored:
            logger.info("Rebuilt %s concurrency slots from PostgreSQL", restored)
        return restored
    except Exception as exc:
        logger.warning("Failed to rebuild slots from PG: %s", exc)
        return 0


def http_429_detail(reject: SlotReject) -> dict:
    return {
        "message": reject.message,
        "error_code": reject.code,
        "retry_after": reject.retry_after,
    }


async def rebuild_slots_from_pg_if_needed() -> int:
    """Public entry for API/worker startup after Redis restart."""
    redis = await _redis()
    if redis is None:
        return 0
    try:
        global_n = int(await redis.scard(_global_key()) or 0)
        if global_n > 0:
            return 0
        return await _rebuild_slots_from_pg(redis)
    except Exception as exc:
        logger.warning("startup slot rebuild failed: %s", exc)
        return 0
