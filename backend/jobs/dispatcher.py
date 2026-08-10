"""Dispatch pending_dispatch jobs to the Redis/ARQ queue."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

DISPATCH_MAX_ATTEMPTS = int(os.getenv("RESEARCH_DISPATCH_MAX_ATTEMPTS", "5"))
DISPATCH_LOOP_INTERVAL_SEC = float(os.getenv("RESEARCH_DISPATCH_INTERVAL_SEC", "10"))


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _dispatch_attempts(checkpoint: dict | None) -> int:
    if not checkpoint:
        return 0
    try:
        return int(checkpoint.get("dispatch_attempts") or 0)
    except (TypeError, ValueError):
        return 0


def _with_dispatch_attempts(checkpoint: dict | None, attempts: int) -> dict:
    data = dict(checkpoint or {})
    data["dispatch_attempts"] = attempts
    return data


async def dispatch_pending_jobs(limit: int = 20) -> int:
    """
    Claim pending_dispatch rows with FOR UPDATE SKIP LOCKED and enqueue to ARQ.

    Returns the number of jobs successfully enqueued.
    """
    from db.session import get_session_factory, is_db_enabled
    from jobs.errors import backoff_seconds

    if not is_db_enabled():
        return await _dispatch_pending_jobs_memory(limit)

    factory = get_session_factory()
    if factory is None:
        return 0

    from db.models import ResearchJob
    from sqlalchemy import or_, select

    dispatched = 0
    now = _utcnow()

    async with factory() as session:
        stmt = (
            select(ResearchJob)
            .where(
                ResearchJob.status == "pending_dispatch",
                or_(
                    ResearchJob.next_retry_at.is_(None),
                    ResearchJob.next_retry_at <= now,
                ),
            )
            .with_for_update(skip_locked=True)
            .limit(limit)
        )
        rows = (await session.execute(stmt)).scalars().all()

        for job in rows:
            dispatch_attempts = _dispatch_attempts(job.checkpoint_json)
            if dispatch_attempts >= DISPATCH_MAX_ATTEMPTS:
                job.status = "failed"
                job.last_error_code = "dispatch_exhausted"
                job.error = f"dispatch exhausted after {DISPATCH_MAX_ATTEMPTS} attempts"
                job.finished_at = now
                job.version = (job.version or 1) + 1
                job.updated_at = now
                continue

            payload = dict(job.payload or {})
            payload.setdefault("user_id", job.user_id)
            payload.setdefault("tenant_id", job.tenant_id)
            if job.session_id:
                payload.setdefault("session_id", str(job.session_id))

            from jobs.worker import enqueue_research_job

            ok = await enqueue_research_job(job.id, payload, stamp_enqueued_at=False)
            if ok:
                job.status = "queued"
                job.enqueued_at = now
                job.progress = "queued"
                job.error = None
                job.last_error_code = None
                job.next_retry_at = None
                job.version = (job.version or 1) + 1
                job.updated_at = now
                dispatched += 1
            else:
                next_attempt = dispatch_attempts + 1
                delay = backoff_seconds(next_attempt)
                job.next_retry_at = now + timedelta(seconds=delay)
                job.checkpoint_json = _with_dispatch_attempts(job.checkpoint_json, next_attempt)
                job.last_error_code = "enqueue_failed"
                job.error = f"enqueue failed; retry in {delay}s (attempt {next_attempt})"
                job.version = (job.version or 1) + 1
                job.updated_at = now
                if next_attempt >= DISPATCH_MAX_ATTEMPTS:
                    job.status = "failed"
                    job.last_error_code = "dispatch_exhausted"
                    job.error = f"dispatch exhausted after {DISPATCH_MAX_ATTEMPTS} attempts"
                    job.finished_at = now

        await session.commit()

    if dispatched:
        logger.info("Dispatched %s pending research job(s)", dispatched)
    return dispatched


async def _dispatch_pending_jobs_memory(limit: int) -> int:
    from jobs import _MEMORY_JOBS, update_job
    from jobs.errors import backoff_seconds
    from jobs.worker import enqueue_research_job

    now = _utcnow()
    dispatched = 0
    candidates: list[tuple[str, dict[str, Any]]] = []
    for jid, job in _MEMORY_JOBS.items():
        if job.get("status") != "pending_dispatch":
            continue
        next_retry = job.get("next_retry_at")
        if next_retry is not None:
            if isinstance(next_retry, (int, float)):
                if next_retry > now.timestamp() * 1000:
                    continue
            elif isinstance(next_retry, datetime) and next_retry > now:
                continue
        dispatch_attempts = _dispatch_attempts(job.get("checkpoint_json"))
        if dispatch_attempts >= DISPATCH_MAX_ATTEMPTS:
            await update_job(
                jid,
                status="failed",
                error=f"dispatch exhausted after {DISPATCH_MAX_ATTEMPTS} attempts",
            )
            continue
        candidates.append((jid, job))
        if len(candidates) >= limit:
            break

    for jid, job in candidates:
        payload = dict(job.get("payload") or {})
        ok = await enqueue_research_job(jid, payload, stamp_enqueued_at=False)
        if ok:
            await update_job(jid, status="queued", progress="queued", error=None)
            job["enqueued_at"] = int(now.timestamp() * 1000)
            job["version"] = int(job.get("version") or 1) + 1
            dispatched += 1
        else:
            next_attempt = _dispatch_attempts(job.get("checkpoint_json")) + 1
            delay = backoff_seconds(next_attempt)
            await update_job(
                jid,
                status="pending_dispatch",
                error=f"enqueue failed; retry in {delay}s (attempt {next_attempt})",
            )
            job["checkpoint_json"] = _with_dispatch_attempts(job.get("checkpoint_json"), next_attempt)
            job["next_retry_at"] = int((now + timedelta(seconds=delay)).timestamp() * 1000)
            job["version"] = int(job.get("version") or 1) + 1
            if next_attempt >= DISPATCH_MAX_ATTEMPTS:
                await update_job(
                    jid,
                    status="failed",
                    error=f"dispatch exhausted after {DISPATCH_MAX_ATTEMPTS} attempts",
                )

    return dispatched


async def dispatcher_loop(stop_event: asyncio.Event) -> None:
    """Background loop: dispatch pending jobs every ~10 seconds."""
    logger.info("Research job dispatcher loop started (interval=%ss)", DISPATCH_LOOP_INTERVAL_SEC)
    while not stop_event.is_set():
        try:
            await dispatch_pending_jobs()
        except Exception as exc:
            logger.exception("Dispatcher loop error: %s", exc)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=DISPATCH_LOOP_INTERVAL_SEC)
        except asyncio.TimeoutError:
            continue
    logger.info("Research job dispatcher loop stopped")
