"""Research job store: PostgreSQL is the source of truth when enabled.

Redis is queue transport + optional progress pub/sub only.
"""

from __future__ import annotations

import asyncio
import logging
import os
import socket
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_MEMORY_JOBS: Dict[str, Dict[str, Any]] = {}

# Lifecycle status (authoritative)
JOB_STATUSES = frozenset(
    {
        "pending_dispatch",
        "queued",
        "running",
        "retrying",
        "stale",
        "cancel_requested",
        "cancelling",
        "completed",
        "failed",
        "cancelled",
    }
)
TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled"})

# Pipeline stage (informational progress)
JOB_STAGES = frozenset({"planning", "researching", "writing", "finalizing", ""})


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _default_worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


def new_job_id() -> str:
    return str(uuid.uuid4())


def is_redis_enabled() -> bool:
    return bool(os.getenv("REDIS_URL", "").strip())


def allow_in_process_research_fallback() -> bool:
    """Dev-only escape hatch. Production must keep this false."""
    env = (
        os.getenv("ENV", "")
        or os.getenv("ENVIRONMENT", "")
        or os.getenv("APP_ENV", "")
    ).strip().lower()
    if env in ("production", "prod"):
        return False
    flag = os.getenv("ALLOW_IN_PROCESS_RESEARCH_FALLBACK", "false").strip().lower()
    return flag in ("1", "true", "yes", "on")


def enable_async_research_jobs() -> bool:
    """New UI path default ON. Set ENABLE_ASYNC_RESEARCH_JOBS=false to force legacy WS."""
    flag = os.getenv("ENABLE_ASYNC_RESEARCH_JOBS", "true").strip().lower()
    return flag not in ("0", "false", "no", "off")


def enable_ws_start_research() -> bool:
    """Legacy WebSocket `start` rollback path. Default OFF in production."""
    env = (
        os.getenv("ENV", "")
        or os.getenv("ENVIRONMENT", "")
        or os.getenv("APP_ENV", "")
    ).strip().lower()
    flag = os.getenv("ENABLE_WS_START_RESEARCH", "").strip().lower()
    if flag in ("1", "true", "yes", "on"):
        return True
    if flag in ("0", "false", "no", "off"):
        return False
    return env not in ("production", "prod")


def _db_required() -> bool:
    return bool(os.getenv("DATABASE_URL", "").strip())


def _dt_to_ms(value: datetime | None) -> int | None:
    if value is None:
        return None
    return int(value.timestamp() * 1000)


def _job_to_dict(job) -> Dict[str, Any]:
    return {
        "id": job.id,
        "user_id": job.user_id,
        "tenant_id": getattr(job, "tenant_id", None) or job.user_id,
        "session_id": str(job.session_id) if job.session_id else None,
        "status": job.status,
        "stage": getattr(job, "stage", None) or "",
        "progress": job.progress,
        "error": job.error,
        "payload": job.payload,
        "result": job.result,
        "attempt": getattr(job, "attempt", 0) or 0,
        "idempotency_key": getattr(job, "idempotency_key", None),
        "heartbeat_at": _dt_to_ms(getattr(job, "heartbeat_at", None)),
        "started_at": _dt_to_ms(getattr(job, "started_at", None)),
        "finished_at": _dt_to_ms(getattr(job, "finished_at", None)),
        "enqueued_at": _dt_to_ms(getattr(job, "enqueued_at", None)),
        "next_retry_at": _dt_to_ms(getattr(job, "next_retry_at", None)),
        "cancel_requested_at": _dt_to_ms(getattr(job, "cancel_requested_at", None)),
        "worker_id": getattr(job, "worker_id", None),
        "last_error_code": getattr(job, "last_error_code", None),
        "checkpoint_json": getattr(job, "checkpoint_json", None),
        "version": getattr(job, "version", 1) or 1,
        "created_at": _dt_to_ms(job.created_at),
        "updated_at": _dt_to_ms(job.updated_at),
    }


def _memory_job_defaults(**overrides: Any) -> Dict[str, Any]:
    now_ms = int(time.time() * 1000)
    data = {
        "status": "pending_dispatch",
        "stage": "planning",
        "progress": "pending_dispatch",
        "error": None,
        "payload": {},
        "result": None,
        "attempt": 0,
        "idempotency_key": None,
        "heartbeat_at": None,
        "started_at": None,
        "finished_at": None,
        "enqueued_at": None,
        "next_retry_at": None,
        "cancel_requested_at": None,
        "worker_id": None,
        "last_error_code": None,
        "checkpoint_json": None,
        "version": 1,
        "created_at": now_ms,
        "updated_at": now_ms,
    }
    data.update(overrides)
    return data


async def create_job(
    *,
    user_id: str = "anonymous",
    tenant_id: str | None = None,
    session_id: str | None = None,
    payload: dict | None = None,
    job_id: str | None = None,
    idempotency_key: str | None = None,
) -> str:
    from security import tenant_id_for

    tid = tenant_id or tenant_id_for(user_id)
    jid = job_id or new_job_id()
    payload = payload or {}

    if idempotency_key:
        existing = await find_job_by_idempotency(tid, idempotency_key, user_id=user_id)
        if existing:
            return existing["id"]

    record = _memory_job_defaults(
        id=jid,
        user_id=user_id,
        tenant_id=tid,
        session_id=session_id,
        payload=payload,
        idempotency_key=idempotency_key,
    )

    try:
        from db.session import get_session_factory, is_db_enabled
        from db.models import ResearchJob
        import uuid as _uuid
        from sqlalchemy.exc import IntegrityError

        if is_db_enabled():
            factory = get_session_factory()
            if factory is not None:
                async with factory() as session:
                    sid = None
                    if session_id:
                        try:
                            sid = _uuid.UUID(session_id)
                        except ValueError:
                            sid = None
                    session.add(
                        ResearchJob(
                            id=jid,
                            session_id=sid,
                            user_id=user_id,
                            tenant_id=tid,
                            status="pending_dispatch",
                            stage="planning",
                            progress="pending_dispatch",
                            payload=payload,
                            attempt=0,
                            idempotency_key=idempotency_key,
                            version=1,
                        )
                    )
                    try:
                        await session.commit()
                    except IntegrityError:
                        await session.rollback()
                        if idempotency_key:
                            raced = await find_job_by_idempotency(
                                tid, idempotency_key, user_id=user_id
                            )
                            if raced:
                                return raced["id"]
                        raise
                _MEMORY_JOBS[jid] = record
                return jid
    except Exception as exc:
        logger.warning("Job DB create failed: %s", exc)
        if _db_required():
            raise

    _MEMORY_JOBS[jid] = record
    return jid


async def find_job_by_idempotency(
    tenant_id: str,
    idempotency_key: str,
    *,
    user_id: str | None = None,
) -> Optional[Dict[str, Any]]:
    try:
        from db.session import get_session_factory, is_db_enabled
        from db.models import ResearchJob
        from sqlalchemy import select

        if is_db_enabled():
            factory = get_session_factory()
            if factory is not None:
                async with factory() as session:
                    stmt = select(ResearchJob).where(
                        ResearchJob.tenant_id == tenant_id,
                        ResearchJob.idempotency_key == idempotency_key,
                    )
                    if user_id is not None:
                        stmt = stmt.where(ResearchJob.user_id == user_id)
                    row = (await session.execute(stmt)).scalar_one_or_none()
                    if row:
                        return _job_to_dict(row)
    except Exception as exc:
        logger.debug("idempotency lookup failed: %s", exc)

    for job in _MEMORY_JOBS.values():
        if job.get("tenant_id") != tenant_id:
            continue
        if job.get("idempotency_key") != idempotency_key:
            continue
        if user_id is not None and job.get("user_id") != user_id:
            continue
        return dict(job)
    return None


async def update_job(
    job_id: str,
    *,
    status: str | None = None,
    stage: str | None = None,
    progress: str | None = None,
    error: str | None = None,
    result: dict | None = None,
    attempt: int | None = None,
    tenant_id: str | None = None,
    user_id: str | None = None,
    last_error_code: str | None = None,
    worker_id: str | None = None,
    heartbeat_at: int | None = None,
    finished_at: int | None = None,
    next_retry_at: int | None = None,
    checkpoint_json: dict | None = None,
    version: int | None = None,
    expected_version: int | None = None,
) -> bool:
    record = _MEMORY_JOBS.get(job_id)
    if record is None:
        record = {"id": job_id}
        _MEMORY_JOBS[job_id] = record
    if status is not None:
        record["status"] = status
    if stage is not None:
        record["stage"] = stage
    if progress is not None:
        record["progress"] = progress
    if error is not None:
        record["error"] = error
    if result is not None:
        record["result"] = result
    if attempt is not None:
        record["attempt"] = attempt
    if last_error_code is not None:
        record["last_error_code"] = last_error_code
    if worker_id is not None:
        record["worker_id"] = worker_id
    if heartbeat_at is not None:
        record["heartbeat_at"] = heartbeat_at
    if finished_at is not None:
        record["finished_at"] = finished_at
    if next_retry_at is not None:
        record["next_retry_at"] = next_retry_at
    if checkpoint_json is not None:
        record["checkpoint_json"] = checkpoint_json
    if version is not None:
        record["version"] = version
    elif expected_version is not None:
        record["version"] = expected_version + 1
    record["updated_at"] = int(time.time() * 1000)

    try:
        from db.session import get_session_factory, is_db_enabled
        from db.models import ResearchJob
        from sqlalchemy import update

        if is_db_enabled():
            factory = get_session_factory()
            if factory is not None:
                async with factory() as session:
                    values: Dict[str, Any] = {"updated_at": _utcnow()}
                    if status is not None:
                        values["status"] = status
                    if stage is not None:
                        values["stage"] = stage
                    if progress is not None:
                        values["progress"] = progress
                    if error is not None:
                        values["error"] = error
                    if result is not None:
                        values["result"] = result
                    if attempt is not None:
                        values["attempt"] = attempt
                    if last_error_code is not None:
                        values["last_error_code"] = last_error_code
                    if worker_id is not None:
                        values["worker_id"] = worker_id
                    if heartbeat_at is not None:
                        values["heartbeat_at"] = datetime.fromtimestamp(
                            heartbeat_at / 1000, tz=timezone.utc
                        )
                    if finished_at is not None:
                        values["finished_at"] = datetime.fromtimestamp(
                            finished_at / 1000, tz=timezone.utc
                        )
                    if next_retry_at is not None:
                        values["next_retry_at"] = datetime.fromtimestamp(
                            next_retry_at / 1000, tz=timezone.utc
                        )
                    if checkpoint_json is not None:
                        values["checkpoint_json"] = checkpoint_json
                    if version is not None:
                        values["version"] = version
                    elif expected_version is not None:
                        values["version"] = expected_version + 1

                    stmt = update(ResearchJob).where(ResearchJob.id == job_id)
                    if expected_version is not None:
                        stmt = stmt.where(ResearchJob.version == expected_version)
                    stmt = stmt.values(**values)
                    result_proxy = await session.execute(stmt)
                    if result_proxy.rowcount == 0:
                        await session.rollback()
                        return False
                    await session.commit()
                    return True
    except Exception as exc:
        logger.warning("Job DB update failed (memory mirror kept): %s", exc)
    return True


async def get_job(
    job_id: str,
    *,
    tenant_id: str | None = None,
    user_id: str | None = None,
) -> Optional[Dict[str, Any]]:
    """Read job. Prefer PostgreSQL when enabled."""
    try:
        from db.session import get_session_factory, is_db_enabled
        from db.models import ResearchJob

        if is_db_enabled():
            factory = get_session_factory()
            if factory is not None:
                async with factory() as session:
                    job = await session.get(ResearchJob, job_id)
                    if job is None:
                        return None
                    if tenant_id and getattr(job, "tenant_id", None) and job.tenant_id != tenant_id:
                        return None
                    # Always enforce owner match when caller identity is known. :-)
                    if user_id and job.user_id != user_id:
                        return None
                    data = _job_to_dict(job)
                    _MEMORY_JOBS[job_id] = data
                    return data
    except Exception as exc:
        logger.warning("Job DB get failed: %s", exc)

    mem = _MEMORY_JOBS.get(job_id)
    if not mem:
        return None
    if tenant_id and mem.get("tenant_id") and mem.get("tenant_id") != tenant_id:
        return None
    if user_id and mem.get("user_id") != user_id:
        return None
    return dict(mem)


async def cancel_job(
    job_id: str,
    *,
    tenant_id: str | None = None,
    user_id: str | None = None,
) -> bool:
    job = await get_job(job_id, tenant_id=tenant_id, user_id=user_id)
    if job is None:
        return False
    status = job.get("status")
    if status in TERMINAL_STATUSES:
        return status == "cancelled"
    if status in ("cancel_requested", "cancelling"):
        return True

    now = _utcnow()
    now_ms = int(now.timestamp() * 1000)
    # Not yet running → cancel can be terminal immediately (no worker to notify)
    not_started = status in (
        "pending_dispatch",
        "queued",
        "retrying",
        "stale",
    )
    target_status = "cancelled" if not_started else "cancel_requested"
    target_progress = "cancelled" if not_started else "cancel_requested"

    try:
        from db.session import get_session_factory, is_db_enabled
        from db.models import ResearchJob
        from sqlalchemy import update

        if is_db_enabled():
            factory = get_session_factory()
            if factory is not None:
                async with factory() as session:
                    values = {
                        "status": target_status,
                        "cancel_requested_at": now,
                        "progress": target_progress,
                        "last_error_code": "cancelled",
                        "version": ResearchJob.version + 1,
                        "updated_at": now,
                    }
                    if target_status == "cancelled":
                        values["finished_at"] = now
                        values["worker_id"] = None
                    stmt = (
                        update(ResearchJob)
                        .where(
                            ResearchJob.id == job_id,
                            ResearchJob.status.notin_(tuple(TERMINAL_STATUSES)),
                        )
                        .values(**values)
                    )
                    if tenant_id:
                        stmt = stmt.where(ResearchJob.tenant_id == tenant_id)
                    if user_id:
                        stmt = stmt.where(ResearchJob.user_id == user_id)
                    result = await session.execute(stmt)
                    if result.rowcount == 0:
                        await session.rollback()
                        fresh = await get_job(job_id, tenant_id=tenant_id, user_id=user_id)
                        return bool(
                            fresh
                            and fresh.get("status")
                            in ("cancel_requested", "cancelling", "cancelled")
                        )
                    await session.commit()
                    mem = _MEMORY_JOBS.get(job_id) or {"id": job_id}
                    mem.update(
                        {
                            "status": target_status,
                            "cancel_requested_at": now_ms,
                            "progress": target_progress,
                            "last_error_code": "cancelled",
                        }
                    )
                    if target_status == "cancelled":
                        mem["finished_at"] = now_ms
                        mem["worker_id"] = None
                    _MEMORY_JOBS[job_id] = mem
                    if target_status == "cancelled":
                        await _release_job_slots(job_id, job)
                    return True
    except Exception as exc:
        logger.warning("Job cancel DB update failed: %s", exc)
        if _db_required():
            raise

    mem = _MEMORY_JOBS.get(job_id)
    if mem is not None:
        mem["status"] = target_status
        mem["cancel_requested_at"] = now_ms
        mem["progress"] = target_progress
        mem["last_error_code"] = "cancelled"
        mem["updated_at"] = now_ms
        if target_status == "cancelled":
            mem["finished_at"] = now_ms
            mem["worker_id"] = None
    if target_status == "cancelled":
        await _release_job_slots(job_id, job)
    return True


async def _release_job_slots(job_id: str, job: Optional[Dict[str, Any]]) -> None:
    try:
        from jobs.slots import release_slots

        await release_slots(
            job_id=job_id,
            tenant_id=(job or {}).get("tenant_id") or "anonymous",
            user_id=(job or {}).get("user_id") or "anonymous",
        )
    except Exception as exc:
        logger.warning("Slot release on cancel failed for %s: %s", job_id, exc)


async def claim_job_for_worker(
    job_id: str,
    *,
    worker_id: str | None = None,
) -> Optional[Dict[str, Any]]:
    """
    Atomically move a deliverable job to running with worker metadata.

    ``pending_dispatch`` is accepted only when its retry time is due. This
    closes the small transaction window where ARQ can deliver a newly queued
    message before the dispatcher commits its ``pending_dispatch -> queued``
    state update. Terminal states and deferred retries remain unclaimable.
    """
    wid = worker_id or _default_worker_id()
    now = _utcnow()
    now_ms = int(now.timestamp() * 1000)

    try:
        from db.session import get_session_factory, is_db_enabled
        from db.models import ResearchJob
        from sqlalchemy import and_, or_, update

        if is_db_enabled():
            factory = get_session_factory()
            if factory is not None:
                async with factory() as session:
                    stmt = (
                        update(ResearchJob)
                        .where(
                            ResearchJob.id == job_id,
                            or_(
                                ResearchJob.status.in_(("queued", "retrying", "stale")),
                                and_(
                                    ResearchJob.status == "pending_dispatch",
                                    or_(
                                        ResearchJob.next_retry_at.is_(None),
                                        ResearchJob.next_retry_at <= now,
                                    ),
                                ),
                            ),
                        )
                        .values(
                            status="running",
                            worker_id=wid,
                            started_at=now,
                            heartbeat_at=now,
                            stage="planning",
                            progress="research_started",
                            attempt=ResearchJob.attempt + 1,
                            version=ResearchJob.version + 1,
                            updated_at=now,
                        )
                        .returning(ResearchJob)
                    )
                    row = (await session.execute(stmt)).scalar_one_or_none()
                    if row is None:
                        await session.rollback()
                        existing = await get_job(job_id)
                        if existing and existing.get("status") == "running":
                            logger.info(
                                "Skip job %s — already running (duplicate protection)", job_id
                            )
                        elif existing:
                            logger.info(
                                "Skip job %s — unexpected status %s",
                                job_id,
                                existing.get("status"),
                            )
                        return None
                    await session.commit()
                    data = _job_to_dict(row)
                    _MEMORY_JOBS[job_id] = data
                    return data
    except Exception as exc:
        logger.warning("Job claim DB failed, trying memory fallback: %s", exc)
        if _db_required():
            raise

    job = await get_job(job_id)
    if job is None:
        return None
    status = job.get("status")
    if status in TERMINAL_STATUSES:
        logger.info("Skip job %s — already terminal (%s)", job_id, status)
        return None
    if status == "running":
        logger.info("Skip job %s — already running (duplicate protection)", job_id)
        return None
    if status == "pending_dispatch":
        next_retry = job.get("next_retry_at")
        if next_retry is not None:
            if isinstance(next_retry, (int, float)) and next_retry > now_ms:
                logger.info("Skip job %s — dispatch retry is not due", job_id)
                return None
            if isinstance(next_retry, datetime) and next_retry > now:
                logger.info("Skip job %s — dispatch retry is not due", job_id)
                return None
    elif status not in ("queued", "retrying", "stale"):
        logger.info("Skip job %s — unexpected status %s", job_id, status)
        return None

    attempt = int(job.get("attempt") or 0) + 1
    version = int(job.get("version") or 1) + 1
    await update_job(
        job_id,
        status="running",
        stage="planning",
        progress="research_started",
        attempt=attempt,
        worker_id=wid,
        heartbeat_at=now_ms,
        version=version,
    )
    job["status"] = "running"
    job["stage"] = "planning"
    job["attempt"] = attempt
    job["worker_id"] = wid
    job["heartbeat_at"] = now_ms
    job["started_at"] = now_ms
    job["version"] = version
    return job


async def update_job_heartbeat(
    job_id: str,
    worker_id: str,
    version: int,
    *,
    max_retries: int = 3,
) -> bool:
    """Optimistic heartbeat update with short retries on version conflict."""
    now = _utcnow()
    now_ms = int(now.timestamp() * 1000)

    for attempt in range(max_retries):
        try:
            from db.session import get_session_factory, is_db_enabled
            from db.models import ResearchJob
            from sqlalchemy import update

            if is_db_enabled():
                factory = get_session_factory()
                if factory is not None:
                    async with factory() as session:
                        stmt = (
                            update(ResearchJob)
                            .where(
                                ResearchJob.id == job_id,
                                ResearchJob.worker_id == worker_id,
                                ResearchJob.version == version,
                                ResearchJob.status == "running",
                            )
                            .values(
                                heartbeat_at=now,
                                version=ResearchJob.version + 1,
                                updated_at=now,
                            )
                            .returning(ResearchJob.version)
                        )
                        new_version = (await session.execute(stmt)).scalar_one_or_none()
                        if new_version is None:
                            await session.rollback()
                            fresh = await get_job(job_id)
                            if fresh is None:
                                return False
                            if fresh.get("status") != "running":
                                return False
                            if fresh.get("worker_id") != worker_id:
                                return False
                            version = int(fresh.get("version") or version)
                            if attempt + 1 < max_retries:
                                await asyncio.sleep(0.05 * (attempt + 1))
                                continue
                            return False
                        await session.commit()
                        mem = _MEMORY_JOBS.get(job_id)
                        if mem is not None:
                            mem["heartbeat_at"] = now_ms
                            mem["version"] = new_version
                        return True
        except Exception as exc:
            logger.debug("Heartbeat update failed (attempt %s): %s", attempt + 1, exc)
            if attempt + 1 < max_retries:
                await asyncio.sleep(0.05 * (attempt + 1))
                continue
            return False

        mem = _MEMORY_JOBS.get(job_id)
        if mem is None:
            return False
        if mem.get("status") != "running" or mem.get("worker_id") != worker_id:
            return False
        if int(mem.get("version") or 0) != version:
            version = int(mem.get("version") or version)
            if attempt + 1 < max_retries:
                await asyncio.sleep(0.05 * (attempt + 1))
                continue
            return False
        mem["heartbeat_at"] = now_ms
        mem["version"] = version + 1
        return True

    return False
