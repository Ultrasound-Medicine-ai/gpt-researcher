"""Bootstrap research session records when session_id is omitted at submit time."""

from __future__ import annotations

import uuid
from typing import Any, Protocol, runtime_checkable

_IDEMPOTENCY_SESSIONS: dict[str, str] = {}


@runtime_checkable
class ReportStoreLike(Protocol):
    async def upsert_report(
        self, report_id: str, report: dict[str, Any], user_id: str | None = None
    ) -> None: ...


def clear_session_bootstrap_cache() -> None:
    _IDEMPOTENCY_SESSIONS.clear()


async def ensure_research_session(
    *,
    report_store: ReportStoreLike,
    user_id: str,
    tenant_id: str,
    task: str,
    session_id: str | None = None,
    idempotency_key: str | None = None,
    report_language: str = "chinese",
) -> str:
    """Return an existing or newly created session_id (idempotent when key is set)."""
    if session_id:
        return session_id

    cache_key = f"{tenant_id}:{idempotency_key}" if idempotency_key else None
    if cache_key and cache_key in _IDEMPOTENCY_SESSIONS:
        return _IDEMPOTENCY_SESSIONS[cache_key]

    new_id = str(uuid.uuid4())
    await report_store.upsert_report(
        new_id,
        {
            "id": new_id,
            "question": task,
            "status": "running",
            "user_id": user_id,
            "tenant_id": tenant_id,
            "report_language": report_language,
        },
        user_id=None if user_id == "anonymous" else user_id,
    )
    if cache_key:
        _IDEMPOTENCY_SESSIONS[cache_key] = new_id
    return new_id
