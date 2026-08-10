"""Health and readiness probes for production deployments."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


def is_production_env() -> bool:
    env = (
        os.getenv("ENV", "")
        or os.getenv("ENVIRONMENT", "")
        or os.getenv("APP_ENV", "")
    ).strip().lower()
    return env in ("production", "prod")


def _has_model_config() -> bool:
    """Fail-fast when neither cloud nor local LLM endpoint is configured."""
    if os.getenv("OPENAI_API_KEY", "").strip():
        return True
    if os.getenv("AZURE_OPENAI_API_KEY", "").strip():
        return True
    if os.getenv("ANTHROPIC_API_KEY", "").strip():
        return True
    if os.getenv("DASHSCOPE_API_KEY", "").strip():
        return True
    # Local Ollama / custom base URLs without key still count as configured
    if os.getenv("OPENAI_BASE_URL", "").strip() and os.getenv("FAST_LLM", "").strip():
        return True
    return False


async def probe_postgres() -> Tuple[bool, str]:
    try:
        from db.session import get_engine, is_db_enabled

        if not is_db_enabled():
            return False, "DATABASE_URL unset"
        engine = get_engine()
        if engine is None:
            return False, "engine not initialized"
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        return True, "ok"
    except Exception as exc:
        logger.warning("Postgres readiness probe failed: %s", exc)
        return False, "unavailable"


async def probe_redis() -> Tuple[bool, str]:
    url = os.getenv("REDIS_URL", "").strip()
    if not url:
        return False, "REDIS_URL unset"
    try:
        from redis.asyncio import from_url

        client = from_url(url, socket_connect_timeout=2, socket_timeout=2)
        try:
            pong = await client.ping()
            return (True, "ok") if pong else (False, "ping failed")
        finally:
            await client.aclose()
    except Exception as exc:
        logger.warning("Redis readiness probe failed: %s", exc)
        return False, "unavailable"


def probe_migrations() -> Tuple[bool, str]:
    if not os.getenv("DATABASE_URL", "").strip():
        return False, "DATABASE_URL unset"
    try:
        from db.migration_check import (
            check_migrations_up_to_date,
            get_current_revision,
            get_head_revision,
        )

        if check_migrations_up_to_date():
            return True, get_current_revision() or "ok"
        return False, f"current={get_current_revision()} head={get_head_revision()}"
    except Exception as exc:
        logger.warning("Migration readiness probe failed: %s", exc)
        return False, "check_failed"


async def probe_queue() -> Tuple[bool, str]:
    """Queue readiness = Redis reachable (ARQ transport)."""
    ok, detail = await probe_redis()
    return ok, detail


def check_readiness() -> Tuple[bool, List[str]]:
    """
    Sync readiness gate used by unit tests / fail-fast startup.

    In production, DATABASE_URL and REDIS_URL are required.
    When DATABASE_URL is set, Alembic migrations must be up to date.
    """
    issues: List[str] = []
    if is_production_env():
        if not os.getenv("DATABASE_URL", "").strip():
            issues.append("DATABASE_URL is required in production")
        if not os.getenv("REDIS_URL", "").strip():
            issues.append("REDIS_URL is required in production")

    if os.getenv("DATABASE_URL", "").strip():
        try:
            from db.migration_check import check_migrations_up_to_date

            if not check_migrations_up_to_date():
                issues.append("database migrations are not up to date")
        except ImportError:
            issues.append("migration check unavailable")

    return (len(issues) == 0, issues)


async def build_ready_payload() -> Dict[str, Any]:
    """Full readiness payload — never includes connection strings or secrets."""
    issues: List[str] = []
    checks: Dict[str, Any] = {}

    if is_production_env():
        if not os.getenv("DATABASE_URL", "").strip():
            issues.append("DATABASE_URL is required in production")
        if not os.getenv("REDIS_URL", "").strip():
            issues.append("REDIS_URL is required in production")
        if not _has_model_config():
            issues.append("model configuration missing")

    pg_ok, pg_detail = await probe_postgres()
    checks["postgres"] = {"ok": pg_ok, "status": pg_detail}
    if not pg_ok and is_production_env():
        issues.append("postgres unavailable")

    redis_ok, redis_detail = await probe_redis()
    checks["redis"] = {"ok": redis_ok, "status": redis_detail}
    if not redis_ok and is_production_env():
        issues.append("redis unavailable")

    mig_ok, mig_detail = probe_migrations()
    checks["migrations"] = {"ok": mig_ok, "status": mig_detail}
    if not mig_ok and os.getenv("DATABASE_URL", "").strip():
        issues.append("migrations not current")

    queue_ok, queue_detail = await probe_queue()
    checks["queue"] = {"ok": queue_ok, "status": queue_detail}

    return {
        "status": "ready" if not issues else "not_ready",
        "checks": checks,
        "issues": issues,
    }
