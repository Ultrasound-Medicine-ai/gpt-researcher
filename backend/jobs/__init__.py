"""Research job store: PostgreSQL is the source of truth when enabled.

Redis may cache progress only; never treat Redis as authoritative job state.
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# In-memory fallback ONLY when DATABASE_URL is unset
_MEMORY_JOBS: Dict[str, Dict[str, Any]] = {}

TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled"})


def new_job_id() -> str:
    return str(uuid.uuid4())


def is_redis_enabled() -> bool:
    return bool(os.getenv("REDIS_URL", "").strip())


def _job_to_dict(job) -> Dict[str, Any]:
    return {
        "id": job.id,
        "user_id": job.user_id,
        "tenant_id": getattr(job, "tenant_id", None) or job.user_id,
        "session_id": str(job.session_id) if job.session_id else None,
        "status": job.status,
        "progress": job.progress,
        "error": job.error,
        "payload": job.payload,
        "result": job.result,
        "attempt": getattr(job, "attempt", 0) or 0,
        "idempotency_key": getattr(job, "idempotency_key", None),
        "created_at": int(job.created_at.timestamp() * 1000) if job.created_at else None,
        "updated_at": int(job.updated_at.timestamp() * 1000) if job.updated_at else None,
    }


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

    # Idempotency: reuse existing non-terminal job with same key for this tenant
    if idempotency_key:
        existing = await find_job_by_idempotency(tid, idempotency_key)
        if existing and existing.get("status") not in TERMINAL_STATUSES:
            return existing["id"]
        if existing and existing.get("status") == "completed":
            return existing["id"]

    record = {
        "id": jid,
        "user_id": user_id,
        "tenant_id": tid,
        "session_id": session_id,
        "status": "queued",
        "progress": "queued",
        "error": None,
        "payload": payload,
        "result": None,
        "attempt": 0,
        "idempotency_key": idempotency_key,
        "created_at": int(time.time() * 1000),
        "updated_at": int(time.time() * 1000),
    }

    try:
        from db.session import get_session_factory, is_db_enabled
        from db.models import ResearchJob
        import uuid as _uuid

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
                            status="queued",
                            progress="queued",
                            payload=payload,
                            attempt=0,
                            idempotency_key=idempotency_key,
                        )
                    )
                    await session.commit()
                # Cache mirror only — PG is authoritative
                _MEMORY_JOBS[jid] = record
                return jid
    except Exception as exc:
        logger.warning("Job DB create failed: %s", exc)
        # Fall through to memory only if DB unavailable
        if _db_required():
            raise

    _MEMORY_JOBS[jid] = record
    return jid


def _db_required() -> bool:
    return bool(os.getenv("DATABASE_URL", "").strip())


async def find_job_by_idempotency(tenant_id: str, idempotency_key: str) -> Optional[Dict[str, Any]]:
    try:
        from db.session import get_session_factory, is_db_enabled
        from db.models import ResearchJob
        from sqlalchemy import select

        if is_db_enabled():
            factory = get_session_factory()
            if factory is not None:
                async with factory() as session:
                    row = (
                        await session.execute(
                            select(ResearchJob).where(
                                ResearchJob.tenant_id == tenant_id,
                                ResearchJob.idempotency_key == idempotency_key,
                            )
                        )
                    ).scalar_one_or_none()
                    if row:
                        return _job_to_dict(row)
    except Exception as exc:
        logger.debug("idempotency lookup failed: %s", exc)

    for job in _MEMORY_JOBS.values():
        if job.get("tenant_id") == tenant_id and job.get("idempotency_key") == idempotency_key:
            return dict(job)
    return None


async def update_job(
    job_id: str,
    *,
    status: str | None = None,
    progress: str | None = None,
    error: str | None = None,
    result: dict | None = None,
    attempt: int | None = None,
    tenant_id: str | None = None,
    user_id: str | None = None,
) -> None:
    # Memory mirror
    record = _MEMORY_JOBS.get(job_id)
    if record is None:
        record = {"id": job_id}
        _MEMORY_JOBS[job_id] = record
    if status is not None:
        record["status"] = status
    if progress is not None:
        record["progress"] = progress
    if error is not None:
        record["error"] = error
    if result is not None:
        record["result"] = result
    if attempt is not None:
        record["attempt"] = attempt
    record["updated_at"] = int(time.time() * 1000)

    try:
        from db.session import get_session_factory, is_db_enabled
        from db.models import ResearchJob

        if is_db_enabled():
            factory = get_session_factory()
            if factory is not None:
                async with factory() as session:
                    job = await session.get(ResearchJob, job_id)
                    if job is None:
                        return
                    # Tenant guard
                    if tenant_id and getattr(job, "tenant_id", None) and job.tenant_id != tenant_id:
                        logger.warning("Refused job update across tenant boundary")
                        return
                    if user_id and job.user_id and job.user_id != user_id and user_id != "anonymous":
                        logger.warning("Refused job update across user boundary")
                        return
                    if status is not None:
                        job.status = status
                    if progress is not None:
                        job.progress = progress
                    if error is not None:
                        job.error = error
                    if result is not None:
                        job.result = result
                    if attempt is not None:
                        job.attempt = attempt
                    await session.commit()
    except Exception as exc:
        logger.warning("Job DB update failed (memory mirror kept): %s", exc)


async def get_job(
    job_id: str,
    *,
    tenant_id: str | None = None,
    user_id: str | None = None,
) -> Optional[Dict[str, Any]]:
    """Read job. Prefer PostgreSQL when enabled — Redis/memory are not authoritative."""
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
                    if user_id and user_id != "anonymous" and job.user_id != user_id:
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
    if user_id and user_id != "anonymous" and mem.get("user_id") != user_id:
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
    if job.get("status") in TERMINAL_STATUSES:
        return job.get("status") == "cancelled"
    await update_job(
        job_id,
        status="cancelled",
        progress="cancelled_by_user",
        tenant_id=tenant_id,
        user_id=user_id,
    )
    return True


async def claim_job_for_worker(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Idempotent claim: only move queued → running once.
    Returns None if already running/terminal (duplicate delivery protection).
    """
    job = await get_job(job_id)
    if job is None:
        return None
    status = job.get("status")
    if status in TERMINAL_STATUSES:
        logger.info("Skip job %s — already terminal (%s)", job_id, status)
        return None
    if status == "running":
        # Duplicate delivery — do not run twice
        logger.info("Skip job %s — already running (duplicate protection)", job_id)
        return None
    attempt = int(job.get("attempt") or 0) + 1
    await update_job(job_id, status="running", progress="research_started", attempt=attempt)
    job["status"] = "running"
    job["attempt"] = attempt
    return job
