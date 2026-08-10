"""Daily model/search budget: Redis window counters + PostgreSQL audit."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


def _env_int(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def daily_max_searches() -> int:
    return _env_int("RESEARCH_DAILY_MAX_SEARCHES", 50)


def daily_max_llm_calls() -> int:
    return _env_int("RESEARCH_DAILY_MAX_LLM_CALLS", 200)


def _utc_day() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _seconds_until_utc_midnight() -> int:
    now = datetime.now(timezone.utc)
    tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0)
    from datetime import timedelta

    tomorrow = tomorrow + timedelta(days=1)
    return max(60, int((tomorrow - now).total_seconds()))


def _key(tenant_id: str, user_id: str, metric: str) -> str:
    return f"gptr:budget:daily:{tenant_id}:{user_id}:{metric}:{_utc_day()}"


class DailyBudgetReject(Exception):
    def __init__(self, code: str, message: str, retry_after: int):
        self.code = code
        self.message = message
        self.retry_after = retry_after
        super().__init__(message)


async def check_daily_budget(*, tenant_id: str, user_id: str) -> None:
    """Raise DailyBudgetReject if Redis daily counters already at/over limit."""
    from jobs.redis_pool import get_redis
    from jobs.slots import retry_after_sec

    redis = await get_redis()
    if redis is None:
        return

    max_s = daily_max_searches()
    max_l = daily_max_llm_calls()
    try:
        searches = int(await redis.get(_key(tenant_id, user_id, "searches")) or 0)
        llm_calls = int(await redis.get(_key(tenant_id, user_id, "llm_calls")) or 0)
    except Exception as exc:
        logger.warning("daily budget read failed: %s", exc)
        return

    # Retry-After: seconds until UTC midnight (budget resets)
    retry = min(_seconds_until_utc_midnight(), max(retry_after_sec(), 60))

    if max_s > 0 and searches >= max_s:
        raise DailyBudgetReject(
            "daily_search_budget_exceeded",
            f"今日搜索预算已用尽（{searches}/{max_s}），请明天再试",
            retry,
        )
    if max_l > 0 and llm_calls >= max_l:
        raise DailyBudgetReject(
            "daily_llm_budget_exceeded",
            f"今日模型调用预算已用尽（{llm_calls}/{max_l}），请明天再试",
            retry,
        )


async def record_job_usage(
    *,
    tenant_id: str,
    user_id: str,
    job_id: str,
    searches: int = 0,
    llm_calls: int = 0,
    completed: bool = False,
) -> None:
    """Increment Redis daily counters and upsert PG audit row."""
    from jobs.redis_pool import get_redis

    redis = await get_redis()
    ttl = _seconds_until_utc_midnight() + 3600
    if redis is not None:
        try:
            if searches:
                key = _key(tenant_id, user_id, "searches")
                await redis.incrby(key, int(searches))
                await redis.expire(key, ttl)
            if llm_calls:
                key = _key(tenant_id, user_id, "llm_calls")
                await redis.incrby(key, int(llm_calls))
                await redis.expire(key, ttl)
            if completed:
                key = _key(tenant_id, user_id, "jobs_completed")
                await redis.incr(key)
                await redis.expire(key, ttl)
        except Exception as exc:
            logger.warning("Redis daily usage incr failed: %s", exc)

    await _upsert_pg_usage(
        tenant_id=tenant_id,
        user_id=user_id,
        searches=searches,
        llm_calls=llm_calls,
        jobs_started=0,
        jobs_completed=1 if completed else 0,
    )


async def record_job_started(*, tenant_id: str, user_id: str) -> None:
    await _upsert_pg_usage(
        tenant_id=tenant_id,
        user_id=user_id,
        searches=0,
        llm_calls=0,
        jobs_started=1,
        jobs_completed=0,
    )


async def _upsert_pg_usage(
    *,
    tenant_id: str,
    user_id: str,
    searches: int,
    llm_calls: int,
    jobs_started: int,
    jobs_completed: int,
) -> None:
    try:
        from db.session import get_session_factory, is_db_enabled
        from db.models import ResearchUsageDaily
        from sqlalchemy.dialects.postgresql import insert
        if not is_db_enabled():
            return
        factory = get_session_factory()
        if factory is None:
            return
        today = datetime.now(timezone.utc).date()
        async with factory() as session:
            stmt = insert(ResearchUsageDaily).values(
                tenant_id=tenant_id,
                user_id=user_id,
                usage_date=today,
                searches=max(0, searches),
                llm_calls=max(0, llm_calls),
                jobs_started=max(0, jobs_started),
                jobs_completed=max(0, jobs_completed),
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["tenant_id", "user_id", "usage_date"],
                set_={
                    "searches": ResearchUsageDaily.searches + max(0, searches),
                    "llm_calls": ResearchUsageDaily.llm_calls + max(0, llm_calls),
                    "jobs_started": ResearchUsageDaily.jobs_started + max(0, jobs_started),
                    "jobs_completed": ResearchUsageDaily.jobs_completed
                    + max(0, jobs_completed),
                    "updated_at": datetime.now(timezone.utc),
                },
            )
            await session.execute(stmt)
            await session.commit()
    except Exception as exc:
        logger.warning("PG usage audit upsert failed: %s", exc)
