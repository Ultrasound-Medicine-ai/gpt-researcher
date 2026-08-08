"""Factory that selects JSON or PostgreSQL report store without changing callers."""

from __future__ import annotations

import logging
from pathlib import Path

from server.report_store import ReportStore

from .session import get_session_factory, is_db_enabled

logger = logging.getLogger(__name__)


def create_report_store(json_path: Path):
    """
    Prefer PostgreSQL when DATABASE_URL is set and initialized.
    Always fall back to JSON file store so report generation never depends on DB.
    """
    if is_db_enabled():
        factory = get_session_factory()
        if factory is not None:
            from .postgres_report_store import PostgresReportStore

            logger.info("Using PostgreSQL report store")
            return PostgresReportStore(factory)

    logger.info("Using JSON report store at %s", json_path)
    return ReportStore(json_path)
