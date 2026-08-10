"""ARQ research worker: claim → run_agent → persist → completed.

PostgreSQL is the authoritative job status store.
Redis is queue transport only (shared pool via redis_pool).
"""

from __future__ import annotations

import asyncio
import logging
import os
import socket
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
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


def _worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _redact_error(msg: str, limit: int = 500) -> str:
    text = (msg or "").replace("\n", " ")
    for marker in ("api_key", "authorization", "bearer ", "sk-", "password"):
        if marker in text.lower():
            return text[:80] + "…[redacted]"
    return text[:limit]


def _build_cost_payload(
    *,
    budget: Any | None,
    runtime: Any | None,
    status: str | None,
) -> dict[str, Any]:
    snap = budget.snapshot() if budget is not None else {}
    cost: dict[str, Any] = {
        "searches": int(snap.get("searches_used") or 0),
        "llm_calls": int(snap.get("llm_calls_used") or 0),
        "status": status,
    }
    if runtime is not None and hasattr(runtime, "cost_trace"):
        cost.update(runtime.cost_trace())
    return cost


async def _release_and_record_usage(
    *,
    job_id: str,
    tenant_id: str,
    user_id: str,
    budget: Any | None,
    runtime: Any | None = None,
) -> None:
    """Release Redis concurrency slot when job is terminal; audit daily usage."""
    from jobs import TERMINAL_STATUSES, get_job
    from jobs.slots import release_slots

    job = await get_job(job_id)
    if not job or job.get("status") not in TERMINAL_STATUSES:
        return

    await release_slots(
        job_id=job_id,
        tenant_id=job.get("tenant_id") or tenant_id or "anonymous",
        user_id=job.get("user_id") or user_id or "anonymous",
    )

    cost = _build_cost_payload(
        budget=budget, runtime=runtime, status=job.get("status")
    )
    searches = int(cost.get("searches") or 0)
    llm_calls = int(cost.get("llm_calls") or 0)
    # Persist per-job cost snapshot for audit (best-effort)
    if searches or llm_calls or cost.get("llm_events"):
        try:
            from jobs import update_job

            result = dict(job.get("result") or {})
            prev = dict(result.get("cost") or {})
            prev.update(cost)
            result["cost"] = prev
            await update_job(job_id, result=result, tenant_id=tenant_id)
        except Exception as exc:
            logger.debug("job cost snapshot skipped: %s", exc)

    try:
        from jobs.daily_budget import record_job_usage

        await record_job_usage(
            tenant_id=job.get("tenant_id") or tenant_id or "anonymous",
            user_id=job.get("user_id") or user_id or "anonymous",
            job_id=job_id,
            searches=searches,
            llm_calls=llm_calls,
            completed=job.get("status") == "completed",
        )
    except Exception as exc:
        logger.debug("daily usage record skipped: %s", exc)


async def _set_job(
    job_id: str,
    *,
    tenant_id: str,
    status: str | None = None,
    stage: str | None = None,
    progress: str | None = None,
    error: str | None = None,
    result: dict | None = None,
    last_error_code: str | None = None,
    worker_id: str | None = None,
    expected_version: int | None = None,
    finished_at: int | None = None,
    next_retry_at: int | None = None,
    checkpoint_json: dict | None = None,
) -> bool:
    from jobs import update_job, TERMINAL_STATUSES, get_job
    from jobs.progress import publish_job_event

    # Never let a stale worker overwrite a terminal / foreign ownership state
    if status in TERMINAL_STATUSES or status in ("retrying", "running", "cancelling"):
        fresh = await get_job(job_id)
        if fresh:
            if fresh.get("status") in TERMINAL_STATUSES and status != fresh.get("status"):
                logger.warning(
                    "Refuse to overwrite terminal job %s (%s → %s)",
                    job_id,
                    fresh.get("status"),
                    status,
                )
                return False
            if worker_id and fresh.get("worker_id") and fresh.get("worker_id") != worker_id:
                if fresh.get("status") == "running":
                    logger.warning(
                        "Refuse status write for job %s — owned by %s not %s",
                        job_id,
                        fresh.get("worker_id"),
                        worker_id,
                    )
                    return False

    ok = await update_job(
        job_id,
        status=status,
        stage=stage,
        progress=progress,
        error=error,
        result=result,
        last_error_code=last_error_code,
        worker_id=worker_id,
        expected_version=expected_version,
        finished_at=finished_at,
        next_retry_at=next_retry_at,
        checkpoint_json=checkpoint_json,
        tenant_id=tenant_id,
    )
    await publish_job_event(
        job_id,
        {
            "type": "job_status",
            "content": "job_status",
            "output": {
                "job_id": job_id,
                "status": status,
                "stage": stage,
                "progress": progress,
                "error": error,
                "last_error_code": last_error_code,
            },
        },
        tenant_id=tenant_id,
    )
    return ok


async def _persist_report_and_sources(
    *,
    session_id: str,
    job_id: str,
    report_text: str,
    research_params: dict[str, Any],
    file_paths: dict[str, Any],
    sources: list[dict[str, Any]],
    tenant_id: str,
) -> dict[str, Any]:
    """Save report + sources + file refs. Raises on failure (blocks completed)."""
    from db.report_store_factory import create_report_store
    from pathlib import Path

    store = create_report_store(
        Path(os.getenv("REPORT_STORE_PATH", os.path.join("data", "reports.json")))
    )
    existing = await store.get_report(session_id) or {}
    # Idempotent: same session_id upserts; never create a second report row
    ordered = list(existing.get("orderedData") or [])
    if report_text.strip():
        ordered = [
            item
            for item in ordered
            if (item or {}).get("type") not in ("report", "reportBlock", "report_complete")
        ]
        ordered.append(
            {
                "type": "report_complete",
                "content": "report",
                "output": report_text,
            }
        )

    payload = {
        **existing,
        "id": session_id,
        "question": research_params.get("task", existing.get("question", "")),
        "answer": report_text,
        "orderedData": ordered,
        "status": "completed",
        "job_id": job_id,
        "user_id": research_params.get("user_id", "anonymous"),
        "tenant_id": tenant_id,
        "report_language": research_params.get("report_language")
        or existing.get("report_language", "chinese"),
        "file_paths": file_paths,
    }
    await store.upsert_report(
        session_id,
        payload,
        user_id=research_params.get("user_id"),
    )
    if sources and hasattr(store, "save_research_sources"):
        await store.save_research_sources(
            session_id,
            sources,
            user_id=research_params.get("user_id"),
            raise_on_error=True,
        )
    # Hybrid RAG: ingest completed report (+ source excerpts) for long-session chat
    try:
        from rag.ingest import ingest_text_document

        uid = research_params.get("user_id") or "anonymous"
        if report_text.strip():
            await ingest_text_document(
                text=report_text,
                title=payload.get("question") or "report",
                uri=f"report:{session_id}",
                source_type="report",
                tenant_id=tenant_id,
                user_id=uid,
                session_id=session_id,
                metadata={"job_id": job_id},
            )
        for src in sources or []:
            body = str(src.get("excerpt") or src.get("raw_content") or "").strip()
            if len(body) < 40:
                continue
            await ingest_text_document(
                text=body,
                title=str(src.get("title") or "")[:200],
                uri=str(src.get("url") or ""),
                source_type="scrape",
                tenant_id=tenant_id,
                user_id=uid,
                session_id=session_id,
                source_url=str(src.get("url") or ""),
                metadata={"source_index": src.get("source_index")},
            )
    except Exception as rag_exc:
        logger.debug("Report RAG ingest skipped: %s", rag_exc)
    return payload


async def _ingest_sources_for_trusted_rag(
    *,
    session_id: str,
    sources: list[dict[str, Any]],
    tenant_id: str,
    user_id: str,
    job_id: str,
) -> None:
    """Ingest research source excerpts before trusted retrieve (best-effort)."""
    try:
        from rag.ingest import ingest_text_document
    except Exception:
        return
    for src in sources or []:
        body = str(src.get("excerpt") or src.get("raw_content") or "").strip()
        if len(body) < 40:
            continue
        try:
            await ingest_text_document(
                text=body,
                title=str(src.get("title") or "")[:200],
                uri=str(src.get("url") or ""),
                source_type="scrape",
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=session_id,
                source_url=str(src.get("url") or ""),
                metadata={"job_id": job_id, "pre_trusted": True},
            )
        except Exception as exc:
            logger.debug("Pre-trusted RAG ingest skipped: %s", exc)


async def _mark_retry_or_fail(
    *,
    job_id: str,
    tenant_id: str,
    worker_id: str,
    attempt: int,
    exc: BaseException,
    version: int,
) -> dict:
    from jobs.errors import backoff_seconds, classify_error

    code, transient = classify_error(exc)
    safe_msg = _redact_error(str(exc))

    if not transient or attempt >= MAX_JOB_ATTEMPTS:
        await _set_job(
            job_id,
            tenant_id=tenant_id,
            status="failed",
            progress="error",
            error=safe_msg,
            last_error_code=code,
            worker_id=worker_id,
            expected_version=version,
            finished_at=int(_utcnow().timestamp() * 1000),
        )
        return {"failed": True, "error_code": code, "retry": False}

    delay = backoff_seconds(attempt)
    next_ms = int((_utcnow() + timedelta(seconds=delay)).timestamp() * 1000)
    await _set_job(
        job_id,
        tenant_id=tenant_id,
        status="retrying",
        progress="retry_scheduled",
        error=safe_msg,
        last_error_code=code,
        worker_id=None,
        expected_version=version,
        next_retry_at=next_ms,
    )
    # Re-enqueue after backoff (ARQ job id is stable → no duplicate execution)
    await asyncio.sleep(min(delay, 2))  # short wait; dispatcher also handles retrying→queue
    from jobs import update_job

    from jobs import get_job

    await update_job(
        job_id,
        status="queued",
        progress="requeued",
        tenant_id=tenant_id,
    )
    job = await get_job(job_id)
    await enqueue_research_job(job_id, (job or {}).get("payload") or {})
    return {"retry": True, "error_code": code, "delay": delay}


async def run_research_job(ctx: dict, job_id: str, research_params: dict[str, Any]) -> dict:
    from jobs import claim_job_for_worker, get_job, update_job
    from jobs.progress import JobProgressSink, publish_job_event
    from jobs.runtime import CancellingProgressSink, JobCancelled, JobRuntime
    from gpt_researcher.utils.enum import Tone
    from server.websocket_manager import run_agent
    from server.server_utils import generate_report_files, sanitize_filename
    from security import (
        filter_safe_urls,
        redact_for_trace,
        sanitize_mcp_configs,
        sanitize_markdown,
        tenant_id_for,
    )

    claimed = await claim_job_for_worker(job_id, worker_id=_worker_id())
    if claimed is None:
        existing = await get_job(job_id)
        return {"skipped": True, "status": (existing or {}).get("status"), "job_id": job_id}

    tenant_id = research_params.get("tenant_id") or tenant_id_for(
        research_params.get("user_id")
    )
    worker_id = claimed.get("worker_id") or _worker_id()
    version = int(claimed.get("version") or 1)
    attempt = int(claimed.get("attempt") or 1)

    if attempt > MAX_JOB_ATTEMPTS:
        await _set_job(
            job_id,
            tenant_id=tenant_id,
            status="failed",
            progress="max_attempts",
            error="max attempts exceeded",
            last_error_code="max_attempts",
            worker_id=worker_id,
            finished_at=int(_utcnow().timestamp() * 1000),
        )
        await _release_and_record_usage(
            job_id=job_id,
            tenant_id=tenant_id,
            user_id=research_params.get("user_id") or "anonymous",
            budget=None,
        )
        return {"failed": True, "reason": "max_attempts"}

    logger.info(
        "Starting research job %s %s",
        job_id,
        redact_for_trace({"tenant_id": tenant_id, "task": research_params.get("task")}),
    )

    from jobs.budget import BudgetExceeded, ResearchBudget, clamp_output_words

    budget = ResearchBudget.from_env_and_payload(research_params)
    # Clamp requested length so prompts + truncation share one hard cap
    research_params = dict(research_params)
    research_params["total_words"] = clamp_output_words(
        research_params.get("total_words"), budget.max_output_words
    )

    # Chat-created reports are knowledge-base first.  We retrieve only within
    # the caller's tenant/user scope, then use web research only when coverage
    # is weak or the task explicitly needs current information.
    try:
        from rag.report_source_policy import choose_report_sources, chunks_as_documents

        source_policy = choose_report_sources(
            research_params.get("task") or "",
            tenant_id=tenant_id,
            user_id=research_params.get("user_id"),
            policy=research_params.get("knowledge_policy") or "web_first",
        )
        if source_policy.get("mode") == "knowledge_base":
            research_params["report_source"] = "langchain_documents"
            research_params["documents"] = chunks_as_documents(source_policy.get("chunks") or [])
        elif (research_params.get("knowledge_policy") or "web_first") == "local_first":
            # The chat policy owns source selection; do not accidentally fall
            # back to a stale UI setting such as local-only when evidence is weak.
            research_params["report_source"] = "web"
        # Never checkpoint raw passages: they may be large and are already in PG.
        source_policy_checkpoint = {
            key: value for key, value in source_policy.items() if key != "chunks"
        }
    except Exception as source_policy_exc:
        logger.warning("Knowledge-base-first source policy failed open to web: %s", source_policy_exc)
        source_policy_checkpoint = {"mode": "web", "reason": "policy_error"}

    runtime = JobRuntime(
        job_id, worker_id, version, tenant_id=tenant_id, budget=budget
    )
    runtime.install()
    await runtime.start_heartbeat()

    sink_inner = JobProgressSink(
        job_id, research_params.get("task") or "research", tenant_id=tenant_id
    )
    sink = CancellingProgressSink(sink_inner, runtime)

    try:
        await runtime.abort_check("pre_plan")
        await runtime.save_checkpoint(
            planning_started=True,
            stage="planning",
            source_policy=source_policy_checkpoint,
        )

        tone_name = research_params.get("tone", "Objective")
        try:
            tone = Tone[tone_name] if isinstance(tone_name, str) else tone_name
        except Exception:
            tone = Tone.Objective

        source_urls = filter_safe_urls(research_params.get("source_urls") or [])
        document_urls = filter_safe_urls(research_params.get("document_urls") or [])
        mcp_configs = sanitize_mcp_configs(research_params.get("mcp_configs") or [])
        mcp_enabled = bool(research_params.get("mcp_enabled", False)) and bool(mcp_configs)

        await _set_job(
            job_id,
            tenant_id=tenant_id,
            status="running",
            stage="researching",
            progress="researching",
            worker_id=worker_id,
        )
        await runtime.abort_check("post_plan")
        await runtime.save_checkpoint(planning_done=True, stage="researching")

        agent_kwargs = dict(
            task=research_params["task"],
            report_type=research_params.get("report_type", "research_report"),
            report_source=research_params.get("report_source", "web"),
            source_urls=source_urls,
            document_urls=document_urls,
            tone=tone,
            websocket=sink,
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
            documents=research_params.get("documents"),
        )

        async def _legacy_full():
            return await run_agent(**agent_kwargs, return_researcher=True)

        async def _research_only():
            from trusted_report.research import gather_research_only

            return await gather_research_only(**agent_kwargs)

        async def _legacy_write(researcher_obj):
            from trusted_report.research import legacy_write_from_researcher

            return await legacy_write_from_researcher(researcher_obj)

        from trusted_report.flags import trusted_report_pipeline_enabled
        from trusted_report.execution import execute_report_job

        session_for_rag = research_params.get("session_id")

        async def _after_research(researcher_obj, sources_list):
            await runtime.check_cancel("post_research")
            await runtime.save_checkpoint(research_done=True, stage="writing")
            await _set_job(
                job_id,
                tenant_id=tenant_id,
                status="running",
                stage="writing",
                progress="writing",
                worker_id=worker_id,
            )
            if session_for_rag and sources_list:
                await _ingest_sources_for_trusted_rag(
                    session_id=session_for_rag,
                    sources=sources_list,
                    tenant_id=tenant_id,
                    user_id=research_params.get("user_id") or "anonymous",
                    job_id=job_id,
                )

        async def _save_trusted_checkpoint(payload: dict) -> None:
            await runtime.save_checkpoint(**payload)

        job_snap = await get_job(job_id, tenant_id=tenant_id) or {}

        async def _after_research_or_legacy(researcher_obj, sources_list):
            # Used only on trusted/shadow paths (research_only). Disabled path
            # updates stages after legacy_full returns.
            await _after_research(researcher_obj, sources_list)

        trust_outcome = await asyncio.wait_for(
            execute_report_job(
                question=research_params.get("task") or "",
                report_type=research_params.get("report_type", "research_report"),
                tenant_id=tenant_id,
                session_id=session_for_rag,
                user_id=research_params.get("user_id"),
                sample_key=job_id,
                force_trusted_sample=bool(
                    research_params.get("force_trusted_sample")
                ),
                research_only_runner=_research_only,
                legacy_full_runner=_legacy_full,
                legacy_write_runner=_legacy_write,
                writing_requirements=str(research_params.get("tone") or ""),
                session_summary=str(research_params.get("task") or "")[:500],
                checkpoint=job_snap.get("checkpoint_json") or {},
                save_checkpoint=_save_trusted_checkpoint,
                after_research=_after_research_or_legacy,
            ),
            timeout=DEFAULT_JOB_TIMEOUT_SEC,
        )
        researcher = trust_outcome.researcher
        sources: list[dict[str, Any]] = []
        if researcher is not None:
            try:
                sources = list(researcher.get_research_sources() or [])
            except Exception:
                sources = []

        trust_fields = trust_outcome.result_metadata()
        if trust_outcome.should_fail_job:
            await _set_job(
                job_id,
                tenant_id=tenant_id,
                status="failed",
                stage="writing",
                progress="citation_audit_failed",
                error=_redact_error(
                    trust_outcome.error_message or "citation audit failed"
                ),
                last_error_code=trust_outcome.error_code or "citation_audit_failed",
                result={
                    "report": "",
                    "draft": (trust_outcome.trusted_pipeline or {}).get("draft"),
                    **trust_fields,
                    "cost": _build_cost_payload(
                        budget=budget, runtime=runtime, status="failed"
                    ),
                },
                worker_id=worker_id,
                finished_at=int(_utcnow().timestamp() * 1000),
            )
            return {
                "failed": True,
                "reason": trust_outcome.error_code or "citation_audit_failed",
                "job_id": job_id,
            }

        # Legacy full path (flag off OR gray miss): stage bookkeeping after run_agent. :-)
        _trust_mode = (trust_outcome.trusted_pipeline or {}).get("mode")
        if _trust_mode == "disabled" or not trusted_report_pipeline_enabled():
            await runtime.check_cancel("post_research")
            await runtime.save_checkpoint(research_done=True, stage="writing")
            await _set_job(
                job_id,
                tenant_id=tenant_id,
                status="running",
                stage="writing",
                progress="writing",
                worker_id=worker_id,
            )

        report_text = sanitize_markdown(trust_outcome.report)
        # Word cap is body-only; 参考文献 / References must not be truncated. :-)
        report_text = budget.enforce_output_words(report_text)
        await runtime.save_checkpoint(report_body_done=True, stage="finalizing")

        await runtime.check_cancel("pre_files")
        await _set_job(
            job_id,
            tenant_id=tenant_id,
            status="running",
            stage="finalizing",
            progress="finalizing",
            worker_id=worker_id,
        )

        file_paths: dict[str, Any] = {}
        try:
            sanitized_filename = sanitize_filename(
                f"task_{int(time.time())}_{research_params.get('task', 'research')}"
            )
            file_paths = await generate_report_files(report_text, sanitized_filename)
            file_paths["json"] = os.path.relpath(sink_inner.log_file)
            await runtime.save_checkpoint(files_done=True, file_paths=file_paths)
        except Exception as file_exc:
            logger.warning("Report file generation failed: %s", file_exc)
            return await _mark_retry_or_fail(
                job_id=job_id,
                tenant_id=tenant_id,
                worker_id=worker_id,
                attempt=attempt,
                exc=file_exc,
                version=runtime.version,
            )

        # Cancel after work but before persist → do NOT write completed report
        await runtime.check_cancel("pre_persist")
        fresh = await get_job(job_id, tenant_id=tenant_id)
        if fresh and fresh.get("status") in (
            "cancel_requested",
            "cancelling",
            "cancelled",
        ):
            await _set_job(
                job_id,
                tenant_id=tenant_id,
                status="cancelled",
                progress="cancelled",
                worker_id=worker_id,
                finished_at=int(_utcnow().timestamp() * 1000),
            )
            return {"cancelled": True, "job_id": job_id}

        session_id = research_params.get("session_id") or (fresh or {}).get("session_id")
        if not session_id:
            await _set_job(
                job_id,
                tenant_id=tenant_id,
                status="failed",
                stage="finalizing",
                progress="persist_failed",
                error="session_id required to persist report before completion",
                last_error_code="missing_session",
                worker_id=worker_id,
                finished_at=int(_utcnow().timestamp() * 1000),
            )
            return {"failed": True, "reason": "missing_session"}

        try:
            await _persist_report_and_sources(
                session_id=session_id,
                job_id=job_id,
                report_text=report_text,
                research_params=research_params,
                file_paths=file_paths,
                sources=sources,
                tenant_id=tenant_id,
            )
            await runtime.save_checkpoint(report_persisted=True)
        except Exception as persist_exc:
            logger.exception("Report persistence failed for job %s", job_id)
            # Persist failure is not completed; may be transient (DB blip)
            return await _mark_retry_or_fail(
                job_id=job_id,
                tenant_id=tenant_id,
                worker_id=worker_id,
                attempt=attempt,
                exc=persist_exc,
                version=runtime.version,
            )

        # Final cancel race: if cancel landed during persist, do not mark completed
        fresh = await get_job(job_id, tenant_id=tenant_id)
        if fresh and fresh.get("status") in (
            "cancel_requested",
            "cancelling",
            "cancelled",
        ):
            await _set_job(
                job_id,
                tenant_id=tenant_id,
                status="cancelled",
                progress="cancelled_after_persist",
                worker_id=worker_id,
                finished_at=int(_utcnow().timestamp() * 1000),
            )
            return {"cancelled": True, "job_id": job_id}

        result = {
            "report": report_text,
            "session_id": session_id,
            "tenant_id": tenant_id,
            "file_paths": file_paths,
            "source_count": len(sources),
            "cost": _build_cost_payload(
                budget=budget, runtime=runtime, status="completed"
            ),
            **trust_fields,
        }
        ok = await _set_job(
            job_id,
            tenant_id=tenant_id,
            status="completed",
            stage="finalizing",
            progress="done",
            result=result,
            worker_id=worker_id,
            finished_at=int(_utcnow().timestamp() * 1000),
        )
        if not ok:
            logger.warning("Completed write refused for job %s (ownership/terminal race)", job_id)
            return {"skipped": True, "reason": "ownership_race", "job_id": job_id}

        await publish_job_event(
            job_id,
            {"type": "report_complete", "content": "report", "output": report_text},
            tenant_id=tenant_id,
        )
        if file_paths:
            await publish_job_event(
                job_id,
                {"type": "path", "output": file_paths},
                tenant_id=tenant_id,
            )
        return result
    except JobCancelled:
        await _set_job(
            job_id,
            tenant_id=tenant_id,
            status="cancelled",
            progress="cancelled",
            last_error_code="cancelled",
            worker_id=worker_id,
            finished_at=int(_utcnow().timestamp() * 1000),
        )
        return {"cancelled": True, "job_id": job_id}
    except BudgetExceeded as exc:
        await _set_job(
            job_id,
            tenant_id=tenant_id,
            status="failed",
            progress="budget_exceeded",
            error=_redact_error(str(exc)),
            last_error_code=getattr(exc, "code", None) or "budget_exceeded",
            worker_id=worker_id,
            finished_at=int(_utcnow().timestamp() * 1000),
            checkpoint_json={"budget": budget.snapshot()},
        )
        return {"failed": True, "reason": "budget_exceeded", "error_code": "budget_exceeded"}
    except asyncio.TimeoutError as exc:
        # Final attempt surfaces timeout clearly; earlier attempts may retry.
        if attempt >= MAX_JOB_ATTEMPTS:
            await _set_job(
                job_id,
                tenant_id=tenant_id,
                status="failed",
                progress="timeout",
                error=f"timeout after {DEFAULT_JOB_TIMEOUT_SEC}s",
                last_error_code="timeout",
                worker_id=worker_id,
                finished_at=int(_utcnow().timestamp() * 1000),
            )
            return {"failed": True, "reason": "timeout", "error_code": "timeout"}
        return await _mark_retry_or_fail(
            job_id=job_id,
            tenant_id=tenant_id,
            worker_id=worker_id,
            attempt=attempt,
            exc=exc,
            version=runtime.version,
        )
    except Exception as exc:
        logger.exception("Research job %s failed", job_id)
        await publish_job_event(
            job_id,
            {"type": "error", "content": "error", "output": f"Error: {_redact_error(str(exc))}"},
            tenant_id=tenant_id,
        )
        return await _mark_retry_or_fail(
            job_id=job_id,
            tenant_id=tenant_id,
            worker_id=worker_id,
            attempt=attempt,
            exc=exc,
            version=runtime.version,
        )
    finally:
        await runtime.stop_heartbeat()
        try:
            await _release_and_record_usage(
                job_id=job_id,
                tenant_id=tenant_id,
                user_id=research_params.get("user_id") or "anonymous",
                budget=budget,
                runtime=runtime,
            )
        except Exception as release_exc:
            logger.warning("Slot/usage cleanup failed for %s: %s", job_id, release_exc)
        runtime.uninstall()


async def enqueue_research_job(
    job_id: str,
    research_params: dict[str, Any],
    *,
    stamp_enqueued_at: bool = True,
) -> bool:
    """Enqueue a delivery message; PostgreSQL state claims prevent duplicate runs.

    ARQ de-duplicates an existing ``_job_id``. A worker crash can leave that
    old Redis record behind, so a stale-job retry must use a fresh delivery ID.
    The durable ``queued -> running`` claim is the execution idempotency guard.
    """
    from jobs.redis_pool import ensure_arq_pool, get_redis_url

    if not get_redis_url():
        logger.error("REDIS_URL unset — cannot enqueue job %s", job_id)
        return False
    try:
        from security import tenant_id_for

        redis = await ensure_arq_pool()
        if redis is None:
            return False
        tenant_id = research_params.get("tenant_id") or tenant_id_for(
            research_params.get("user_id")
        )
        # A retry after a killed worker needs a new queue message. Do not use
        # the ResearchJob ID itself here: ARQ may retain the previous message.
        arq_job = await redis.enqueue_job(
            "run_research_job",
            job_id,
            research_params,
            _job_id=f"research:{job_id}:{uuid.uuid4().hex}",
        )
        if arq_job is None:
            logger.error("ARQ did not create queue message for research job %s", job_id)
            return False
        # The dispatcher already owns a row lock and writes this field in its
        # transaction. A nested update of the same row would self-deadlock.
        if stamp_enqueued_at:
            try:
                from db.session import get_session_factory, is_db_enabled
                from db.models import ResearchJob
                from sqlalchemy import update as sa_update

                if is_db_enabled():
                    factory = get_session_factory()
                    if factory is not None:
                        async with factory() as session:
                            await session.execute(
                                sa_update(ResearchJob)
                                .where(ResearchJob.id == job_id)
                                .values(enqueued_at=_utcnow(), updated_at=_utcnow())
                            )
                            await session.commit()
            except Exception:
                pass
        logger.info("Enqueued research job %s (tenant=%s)", job_id, tenant_id)
        return True
    except Exception as exc:
        # ARQ raises if job id already exists / queued — treat as success (idempotent)
        msg = str(exc).lower()
        if "job" in msg and ("exists" in msg or "already" in msg or "duplicate" in msg):
            logger.info("ARQ job research:%s already present — treating as enqueued", job_id)
            return True
        logger.error("ARQ enqueue failed for job %s: %s", job_id, exc)
        return False


# Back-compat aliases for older imports
def forbid_in_process_jobs() -> bool:
    from jobs import allow_in_process_research_fallback

    return not allow_in_process_research_fallback()


async def _worker_fail_fast() -> None:
    """Worker startup checks — fail fast, never fake-healthy."""
    from server.health import build_ready_payload, is_production_env

    if not os.getenv("DATABASE_URL", "").strip():
        raise RuntimeError("DATABASE_URL required for research-worker")
    if not os.getenv("REDIS_URL", "").strip():
        raise RuntimeError("REDIS_URL required for research-worker")

    payload = await build_ready_payload()
    if payload.get("status") != "ready":
        # Model config is soft in non-prod to ease local testing without keys
        issues = list(payload.get("issues") or [])
        if not is_production_env():
            issues = [i for i in issues if "model configuration" not in i]
        hard = [
            i
            for i in issues
            if "postgres" in i or "redis" in i or "migration" in i or "DATABASE" in i or "REDIS" in i
        ]
        if hard or (is_production_env() and issues):
            raise RuntimeError(f"Worker readiness failed: {issues or hard}")


class WorkerSettings:
    functions = [run_research_job]
    redis_settings = None
    max_jobs = int(os.getenv("ARQ_MAX_JOBS", "2"))
    job_timeout = DEFAULT_JOB_TIMEOUT_SEC

    @staticmethod
    async def on_startup(ctx):
        from jobs.redis_pool import init_arq_pool, get_redis
        from db.session import init_db

        await init_db()
        await init_arq_pool()
        await get_redis()
        try:
            from jobs.slots import rebuild_slots_from_pg_if_needed

            restored = await rebuild_slots_from_pg_if_needed()
            if restored:
                logger.info("Worker restored %s concurrency slot(s) from PG", restored)
        except Exception as exc:
            logger.warning("Worker slot rebuild skipped: %s", exc)
        await _worker_fail_fast()
        logger.info("Research worker started (PG authoritative; shared Redis pool)")

    @staticmethod
    async def on_shutdown(ctx):
        from jobs.redis_pool import close_arq_pool
        from db.session import close_db

        await close_arq_pool()
        await close_db()


def _configure_redis_settings():
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        from arq.connections import RedisSettings

        WorkerSettings.redis_settings = RedisSettings.from_dsn(redis_url)
    except Exception:
        pass


_configure_redis_settings()
