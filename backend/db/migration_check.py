"""Migration readiness checks for health/ready probes."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_BACKEND_DIR = Path(__file__).resolve().parents[1]


def _sync_database_url() -> Optional[str]:
    url = (os.getenv("DATABASE_URL") or "").strip()
    if not url:
        return None
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def _alembic_config():
    from alembic.config import Config

    ini_path = _BACKEND_DIR / "alembic.ini"
    cfg = Config(str(ini_path))
    # Always resolve script_location against backend/, not process cwd
    cfg.set_main_option("script_location", str(_BACKEND_DIR / "alembic"))
    sync_url = _sync_database_url()
    if sync_url:
        cfg.set_main_option("sqlalchemy.url", sync_url)
    return cfg


def get_head_revision() -> Optional[str]:
    """Return the latest revision id from the Alembic script directory."""
    try:
        from alembic.script import ScriptDirectory

        cfg = _alembic_config()
        script = ScriptDirectory.from_config(cfg)
        head = script.get_current_head()
        return head
    except Exception as exc:
        logger.warning("Unable to resolve Alembic head revision: %s", exc)
        return None


def get_current_revision() -> Optional[str]:
    """Return the revision stored in alembic_version, or None if unset."""
    sync_url = _sync_database_url()
    if not sync_url:
        return None
    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(sync_url, pool_pre_ping=True)
        with engine.connect() as conn:
            try:
                row = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()
                return str(row) if row else None
            except Exception:
                return None
    except Exception as exc:
        logger.warning("Unable to read alembic_version: %s", exc)
        return None


def check_migrations_up_to_date() -> bool:
    """True when DATABASE_URL is unset (JSON mode) or DB revision matches Alembic head."""
    if not _sync_database_url():
        return True
    head = get_head_revision()
    current = get_current_revision()
    if head is None:
        return False
    if current is None:
        return False
    return current == head
