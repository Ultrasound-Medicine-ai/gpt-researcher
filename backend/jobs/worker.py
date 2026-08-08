"""ARQ research worker with idempotent claim, timeout, and cancel checks.

Quality invariant: generation still calls the same run_agent path.
PostgreSQL remains the authoritative job status store.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from typing import Any

logger = logging.getLogger(__name__)

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)
_ROOT = os.path.abspath(os.path.join(_BACKEND_DIR, ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

DEFAULT_JOB_TIMEOUT_SEC = int(os.getenv("RESEARCH_JOB_TIMEOUT_SEC", "1800"))
MAX_JOB_ATTEMPTS = int(os.getenv("RESEARCH_JOB_MAX_ATTEMPTS", "3"))


async def run_research_job(ctx: dict, job_id: str, research_params: dict[str, Any]) -> dict:
    from jobs import claim_job_for_worker, get_job, update_job
    from gpt_researcher.utils.enum import Tone
    from server.websocket_manager import run_agent
    from security import (
        filter_safe_urls,
        redact_for_trace,
        sanitize_mcp_configs,
        sanitize_markdown,
        tenant_id_for,
    )

    claimed = await claim_job_for_worker(job_id)
    if claimed is None:
        existing = await get_job(job_id)
        return {"skipped": True, "status": (existing or {}).get("status"), "job_id": job_id}

    if int(claimed.get("attempt") or 1) > MAX_JOB_ATTEMPTS:
        await update_job(job_id, status="failed", progress="max_attempts", error="max attempts exceeded")
        return {"failed": True, "reason": "max_attempts"}

    tenant_id = research_params.get("tenant_id") or tenant_id_for(
        research_params.get("user_id")
    )
    logger.info(
        "Starting research job %s %s",
        job_id,
        redact_for_trace({"tenant_id": tenant_id, "task": research_params.get("task")}),
    )

    # Cancel check before heavy work
    fresh = await get_job(job_id, tenant_id=tenant_id)
    if fresh and fresh.get("status") == "cancelled":
        return {"cancelled": True, "job_id": job_id}

    try:
        tone_name = research_params.get("tone", "Objective")
        try:
            tone = Tone[tone_name] if isinstance(tone_name, str) else tone_name
        except Exception:
            tone = Tone.Objective

        source_urls = filter_safe_urls(research_params.get("source_urls") or [])
        document_urls = filter_safe_urls(research_params.get("document_urls") or [])
        mcp_configs = sanitize_mcp_configs(research_params.get("mcp_configs") or [])
        mcp_enabled = bool(research_params.get("mcp_enabled", False)) and bool(mcp_configs)

        async def _run():
            return await run_agent(
                task=research_params["task"],
                report_type=research_params.get("report_type", "research_report"),
                report_source=research_params.get("report_source", "web"),
                source_urls=source_urls,
                document_urls=document_urls,
                tone=tone,
                websocket=None,
                headers=research_params.get("headers"),
                query_domains=research_params.get("query_domains") or [],
                config_path=research_params.get("config_path")
                or os.environ.get("CONFIG_PATH", "default"),
                mcp_enabled=mcp_enabled,
                mcp_strategy=research_params.get("mcp_strategy") or "fast",
                mcp_configs=mcp_configs,
                max_search_results=research_params.get("max_search_results"),
                total_words=research_params.get("total_words"),
                report_language=research_params.get("report_language"),
            )

        report = await asyncio.wait_for(_run(), timeout=DEFAULT_JOB_TIMEOUT_SEC)

        # Cancel may have been requested during run
        fresh = await get_job(job_id, tenant_id=tenant_id)
        if fresh and fresh.get("status") == "cancelled":
            return {"cancelled": True, "job_id": job_id}

        report_text = report if isinstance(report, str) else str(report)
        report_text = sanitize_markdown(report_text)
        result = {
            "report": report_text,
            "session_id": research_params.get("session_id"),
            "tenant_id": tenant_id,
        }
        await update_job(
            job_id,
            status="completed",
            progress="done",
            result=result,
            tenant_id=tenant_id,
        )

        try:
            session_id = research_params.get("session_id")
            if session_id and report_text.strip():
                from db.report_store_factory import create_report_store
                from pathlib import Path

                store = create_report_store(
                    Path(os.getenv("REPORT_STORE_PATH", os.path.join("data", "reports.json")))
                )
                existing = await store.get_report(session_id) or {}
                await store.upsert_report(
                    session_id,
                    {
                        **existing,
                        "id": session_id,
                        "question": research_params.get("task", existing.get("question", "")),
                        "answer": report_text,
                        "status": "completed",
                        "job_id": job_id,
                        "user_id": research_params.get("user_id", "anonymous"),
                        "tenant_id": tenant_id,
                        "report_language": research_params.get("report_language")
                        or existing.get("report_language", "chinese"),
                    },
                    user_id=research_params.get("user_id"),
                )
        except Exception as persist_exc:
            logger.warning(
                "Post-report persistence failed (report still completed): %s", persist_exc
            )

        return result
    except asyncio.TimeoutError:
        await update_job(
            job_id,
            status="failed",
            progress="timeout",
            error=f"timeout after {DEFAULT_JOB_TIMEOUT_SEC}s",
            tenant_id=tenant_id,
        )
        raise
    except Exception as exc:
        logger.exception("Research job %s failed", job_id)
        await update_job(
            job_id,
            status="failed",
            progress="error",
            error=str(exc)[:2000],
            tenant_id=tenant_id,
        )
        raise


async def enqueue_research_job(job_id: str, research_params: dict[str, Any]) -> bool:
    """Enqueue via Redis/ARQ. Returns False so caller can fall back in-process."""
    redis_url = os.getenv("REDIS_URL", "").strip()
    if not redis_url:
        return False
    try:
        from arq import create_pool
        from arq.connections import RedisSettings
        from security import redis_key, tenant_id_for

        tenant_id = research_params.get("tenant_id") or tenant_id_for(
            research_params.get("user_id")
        )
        # Progress cache key is namespaced; authoritative state stays in PG
        _ = redis_key(tenant_id, "job", job_id, "progress")

        redis = await create_pool(RedisSettings.from_dsn(redis_url))
        await redis.enqueue_job("run_research_job", job_id, research_params)
        await redis.close()
        return True
    except Exception as exc:
        logger.warning("ARQ enqueue failed, caller should fall back in-process: %s", exc)
        return False


class WorkerSettings:
    functions = [run_research_job]
    redis_settings = None
    max_jobs = int(os.getenv("ARQ_MAX_JOBS", "2"))
    job_timeout = DEFAULT_JOB_TIMEOUT_SEC

    @staticmethod
    def on_startup(ctx):
        logger.info("Research worker started (PG is job state source of truth)")


def _configure_redis_settings():
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        from arq.connections import RedisSettings

        WorkerSettings.redis_settings = RedisSettings.from_dsn(redis_url)
    except Exception:
        pass


_configure_redis_settings()
