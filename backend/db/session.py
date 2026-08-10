"""SQLAlchemy async engine helpers.

Production startup must NOT mutate schema — Alembic owns migrations.
Dev may still call create_all when ALLOW_DEV_CREATE_ALL=true.
"""

from __future__ import annotations

import logging
import os
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = logging.getLogger(__name__)

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_database_url() -> Optional[str]:
    """Return async SQLAlchemy URL if DATABASE_URL is configured."""
    url = (os.getenv("DATABASE_URL") or "").strip()
    if not url:
        return None
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql+psycopg://"):
        return url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


def is_db_enabled() -> bool:
    return bool(get_database_url())


def get_engine() -> Optional[AsyncEngine]:
    return _engine


def get_session_factory() -> Optional[async_sessionmaker[AsyncSession]]:
    return _session_factory


def _is_production() -> bool:
    env = (
        os.getenv("ENV", "")
        or os.getenv("ENVIRONMENT", "")
        or os.getenv("APP_ENV", "")
    ).strip().lower()
    return env in ("production", "prod")


def _allow_dev_create_all() -> bool:
    if _is_production():
        return False
    flag = os.getenv("ALLOW_DEV_CREATE_ALL", "false").strip().lower()
    return flag in ("1", "true", "yes", "on")


async def init_db() -> bool:
    """
    Initialize engine/session factory.

    Does not run ALTER TABLE. Schema changes belong to Alembic.
    Optionally create_all in non-production when ALLOW_DEV_CREATE_ALL=true.
    """
    global _engine, _session_factory

    url = get_database_url()
    if not url:
        logger.info("DATABASE_URL not set — using local JSON report store")
        return False

    _engine = create_async_engine(url, pool_pre_ping=True, echo=False)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)

    # Connectivity probe
    async with _engine.begin() as conn:
        await conn.execute(__import__("sqlalchemy").text("SELECT 1"))

        if _allow_dev_create_all():
            from .models import Base

            await conn.run_sync(Base.metadata.create_all)
            try:
                await conn.execute(
                    __import__("sqlalchemy").text("CREATE EXTENSION IF NOT EXISTS vector")
                )
            except Exception as exc:
                logger.warning("pgvector extension unavailable: %s", exc)

    logger.info("PostgreSQL engine ready (schema managed by Alembic)")
    return True


async def close_db() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    if _session_factory is None:
        raise RuntimeError("Database is not initialized")
    async with _session_factory() as session:
        yield session
