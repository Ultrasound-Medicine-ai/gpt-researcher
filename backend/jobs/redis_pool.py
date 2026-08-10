"""Shared Redis/ARQ connection pool (lifespan-managed).

Do not create_pool/close per request — reuse the pool from FastAPI lifespan
or worker process startup.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

_pool: Any = None
_redis: Any = None


def get_redis_url() -> str:
    return (os.getenv("REDIS_URL") or "").strip()


def get_arq_pool() -> Any:
    return _pool


async def init_arq_pool() -> bool:
    """Create shared ARQ pool. Returns True if ready."""
    global _pool
    if _pool is not None:
        try:
            # arq Redis pool exposes ping via underlying connection
            await _pool.ping()
            return True
        except Exception:
            logger.warning("ARQ pool stale after Redis restart — recreating")
            try:
                await _pool.close()
            except Exception:
                pass
            _pool = None

    redis_url = get_redis_url()
    if not redis_url:
        logger.info("REDIS_URL unset — ARQ pool not started")
        return False
    try:
        from arq import create_pool
        from arq.connections import RedisSettings

        _pool = await create_pool(RedisSettings.from_dsn(redis_url))
        logger.info("Shared ARQ/Redis pool ready")
        return True
    except Exception as exc:
        logger.error("Failed to init ARQ pool: %s", exc)
        _pool = None
        return False


async def get_redis() -> Optional[Any]:
    """Raw redis.asyncio client for slots/budget (separate from ARQ pool).

    Reconnects after Redis restart — a stale client after ``docker restart``
    would otherwise leave slot release/acquire silently broken.
    """
    global _redis
    if _redis is not None:
        try:
            await _redis.ping()
            return _redis
        except Exception:
            logger.warning("Redis client stale — reconnecting")
            try:
                await _redis.aclose()
            except Exception:
                try:
                    await _redis.close()
                except Exception:
                    pass
            _redis = None

    redis_url = get_redis_url()
    if not redis_url:
        return None
    try:
        from redis.asyncio import from_url

        _redis = from_url(redis_url, decode_responses=True)
        await _redis.ping()
        return _redis
    except Exception as exc:
        logger.warning("Raw Redis client unavailable: %s", exc)
        _redis = None
        return None


async def close_arq_pool() -> None:
    global _pool, _redis
    if _pool is not None:
        try:
            await _pool.close()
        except Exception as exc:
            logger.debug("ARQ pool close: %s", exc)
        _pool = None
    if _redis is not None:
        try:
            await _redis.aclose()
        except Exception:
            try:
                await _redis.close()
            except Exception as exc:
                logger.debug("Redis client close: %s", exc)
        _redis = None


async def ensure_arq_pool() -> Optional[Any]:
    """Return pool, initializing / reconnecting if needed."""
    ok = await init_arq_pool()
    return _pool if ok else None
