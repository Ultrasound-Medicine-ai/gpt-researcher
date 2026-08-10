"""Reap stale running jobs and re-queue or fail them."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

STALE_AFTER_SEC = int(os.getenv("RESEARCH_JOB_STALE_SEC", "90"))
REAPER_LOOP_INTERVAL_SEC = float(os.getenv("RESEARCH_JOB_REAPER_INTERVAL_SEC", "30"))
MAX_JOB_ATTEMPTS = int(os.getenv("RESEARCH_JOB_MAX_ATTEMPTS", "3"))


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def reap_stale_jobs(stale_after_sec: int = STALE_AFTER_SEC) -> int:
    """
    Find running jobs with stale heartbeats and mark stale → retry or failed.

    Returns the number of jobs transitioned out of running.
    """
    from db.session import get_session_factory, is_db_enabled

    if not is_db_enabled():
        reaped = await _reap_stale_jobs_memory(stale_after_sec)
    else:
        factory = get_session_factory()
        if factory is None:
            return 0

        from db.models import ResearchJob
        from sqlalchemy import and_, or_, select, update

        now = _utcnow()
        cutoff = now - timedelta(seconds=stale_after_sec)
        reaped = 0
        failed_for_slots: list[tuple[str, str, str]] = []

        async with factory() as session:
            stmt = select(ResearchJob).where(
                ResearchJob.status == "running",
                or_(
                    and_(
                        ResearchJob.heartbeat_at.is_not(None),
                        ResearchJob.heartbeat_at < cutoff,
                    ),
                    and_(
                        ResearchJob.heartbeat_at.is_(None),
                        ResearchJob.started_at.is_not(None),
                        ResearchJob.started_at < cutoff,
                    ),
                ),
            )
            stale_rows = (await session.execute(stmt)).scalars().all()

            for job in stale_rows:
                old_worker = job.worker_id
                old_version = job.version or 1
                attempt = int(job.attempt or 0)

                mark_stmt = (
                    update(ResearchJob)
                    .where(
                        ResearchJob.id == job.id,
                        ResearchJob.version == old_version,
                        ResearchJob.worker_id == old_worker,
                        ResearchJob.status == "running",
                    )
                    .values(
                        status="stale",
                        last_error_code="stale_worker",
                        progress="stale_detected",
                        error=f"worker heartbeat stale after {stale_after_sec}s",
                        version=old_version + 1,
                        updated_at=now,
                    )
                    .returning(ResearchJob.id)
                )
                marked = (await session.execute(mark_stmt)).scalar_one_or_none()
                if marked is None:
                    continue

                reaped += 1
                new_version = old_version + 1

                if attempt < MAX_JOB_ATTEMPTS:
                    # A durable pending state is written before the Redis side effect.
                    retry_stmt = (
                        update(ResearchJob)
                        .where(
                            ResearchJob.id == job.id,
                            ResearchJob.version == new_version,
                            ResearchJob.status == "stale",
                        )
                        .values(
                            status="pending_dispatch",
                            worker_id=None,
                            heartbeat_at=None,
                            started_at=None,
                            next_retry_at=now,
                            last_error_code="stale_worker",
                            progress="stale_requeued",
                            version=new_version + 1,
                            updated_at=now,
                        )
                    )
                    await session.execute(retry_stmt)
                else:
                    fail_stmt = (
                        update(ResearchJob)
                        .where(
                            ResearchJob.id == job.id,
                            ResearchJob.version == new_version,
                            ResearchJob.status == "stale",
                        )
                        .values(
                            status="failed",
                            worker_id=None,
                            last_error_code="stale_exhausted",
                            error=f"stale worker; max attempts ({MAX_JOB_ATTEMPTS}) exceeded",
                            finished_at=now,
                            progress="stale_exhausted",
                            version=new_version + 1,
                            updated_at=now,
                        )
                    )
                    await session.execute(fail_stmt)
                    failed_for_slots.append(
                        (
                            job.id,
                            job.tenant_id or "anonymous",
                            job.user_id or "anonymous",
                        )
                    )

            await session.commit()

        for jid, tid, uid in failed_for_slots:
            try:
                from jobs.slots import release_slots

                await release_slots(job_id=jid, tenant_id=tid, user_id=uid)
            except Exception as exc:
                logger.debug("slot release after stale fail %s: %s", jid, exc)

    if reaped:
        logger.warning("Reaped %s stale research job(s)", reaped)
        # Do not wait for the next dispatcher tick.  The pending row is already
        # committed, so this performs the Redis side effect safely; the normal
        # dispatcher loop remains the retry path if Redis is unavailable.
        try:
            from jobs.dispatcher import dispatch_pending_jobs

            dispatched = await dispatch_pending_jobs()
            logger.info("Immediately dispatched %s reaped research job(s)", dispatched)
        except Exception:
            logger.exception("Immediate dispatch of reaped jobs failed")
    return reaped


async def _reap_stale_jobs_memory(stale_after_sec: int) -> int:
    from jobs import _MEMORY_JOBS, TERMINAL_STATUSES, update_job

    now = _utcnow()
    cutoff_ms = int((now - timedelta(seconds=stale_after_sec)).timestamp() * 1000)
    reaped = 0

    for jid, job in list(_MEMORY_JOBS.items()):
        if job.get("status") != "running":
            continue
        heartbeat = job.get("heartbeat_at")
        started = job.get("started_at")
        stale = False
        if heartbeat is not None:
            hb_ms = heartbeat if isinstance(heartbeat, (int, float)) else int(heartbeat.timestamp() * 1000)
            stale = hb_ms < cutoff_ms
        elif started is not None:
            st_ms = started if isinstance(started, (int, float)) else int(started.timestamp() * 1000)
            stale = st_ms < cutoff_ms
        if not stale:
            continue

        attempt = int(job.get("attempt") or 0)
        await update_job(
            jid,
            status="stale",
            progress="stale_detected",
            error=f"worker heartbeat stale after {stale_after_sec}s",
        )
        reaped += 1
        if attempt < MAX_JOB_ATTEMPTS:
            await update_job(
                jid,
                status="pending_dispatch",
                progress="stale_requeued",
                last_error_code="stale_worker",
            )
            job["worker_id"] = None
            job["heartbeat_at"] = None
            job["started_at"] = None
            job["next_retry_at"] = int(now.timestamp() * 1000)
        else:
            await update_job(
                jid,
                status="failed",
                progress="stale_exhausted",
                error=f"stale worker; max attempts ({MAX_JOB_ATTEMPTS}) exceeded",
            )
            try:
                from jobs.slots import release_slots

                await release_slots(
                    job_id=jid,
                    tenant_id=job.get("tenant_id") or "anonymous",
                    user_id=job.get("user_id") or "anonymous",
                )
            except Exception as exc:
                logger.debug("slot release after stale fail %s: %s", jid, exc)
        job["version"] = int(job.get("version") or 1) + 1

    return reaped


async def reaper_loop(stop_event: asyncio.Event) -> None:
    """Background loop: stale jobs + leaked concurrency slots every ~30s."""
    logger.info("Research job reaper loop started (interval=%ss)", REAPER_LOOP_INTERVAL_SEC)
    while not stop_event.is_set():
        try:
            await reap_stale_jobs()
        except Exception as exc:
            logger.exception("Reaper loop error: %s", exc)
        try:
            from jobs.slots import reap_leaked_slots

            await reap_leaked_slots()
        except Exception as exc:
            logger.warning("Slot leak reaper error: %s", exc)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=REAPER_LOOP_INTERVAL_SEC)
        except asyncio.TimeoutError:
            continue
    logger.info("Research job reaper loop stopped")
