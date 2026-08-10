"""Trusted job execution modes with authenticity guarantees.

Normal (enabled, not shadow):
  research_only → trusted Planner/Evidence/Claim/Writer → Audit → (persist by caller)
  NO legacy write_report unless fallback after trusted failure.

Shadow:
  research_only → (legacy write + trusted write) → deliver legacy only

Fallback:
  trusted fail before persist → exactly one legacy write → deliver legacy_unverified
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Optional

from trusted_report.flags import (
    trusted_report_fallback_to_legacy,
    trusted_report_pipeline_enabled,
    trusted_report_shadow_mode,
)
from trusted_report.gray import record_release_anomaly, should_use_trusted_pipeline
from trusted_report.models import AuditResult, CitationAuditFailed, TrustOutcome
from trusted_report.pipeline import run_trusted_write_pipeline
from trusted_report.eval import shadow_compare
from trusted_report.tracing import stage_span

logger = logging.getLogger(__name__)


@dataclass
class ExecutionTrace:
    """Observability for authenticity gates (also stored in result)."""

    mode: str = "disabled"
    research_only: bool = False
    trusted_write: bool = False
    legacy_write: bool = False
    legacy_write_count: int = 0
    legacy_write_reason: str = ""  # "" | shadow | fallback | disabled_full_path
    used_legacy_body_as_claim_source: bool = False  # must stay False
    writer_received_only_verified_claims: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


async def execute_report_job(
    *,
    question: str,
    report_type: str,
    tenant_id: str,
    session_id: Optional[str],
    user_id: Optional[str],
    research_only_runner: Callable[..., Any],
    legacy_full_runner: Callable[..., Any],
    legacy_write_runner: Callable[..., Any],
    writing_requirements: str = "",
    session_summary: str = "",
    checkpoint: Optional[dict[str, Any]] = None,
    save_checkpoint: Optional[Callable[[dict], Any]] = None,
    llm_call: Optional[Callable[..., Any]] = None,
    retrieve_fn: Optional[Callable[..., list]] = None,
    document_map_entries: Optional[list] = None,
    after_research: Optional[Callable[..., Any]] = None,
    sample_key: Optional[str] = None,
    force_trusted_sample: bool = False,
) -> TrustOutcome:
    """
    Top-level orchestrator.

    - research_only_runner: async () -> (researcher, sources)
    - legacy_full_runner: async () -> (report, researcher)  # flag-off / gray-miss path
    - legacy_write_runner: async (researcher) -> report_str  # shadow/fallback write only
    - after_research: optional async (researcher, sources) -> None  # e.g. RAG ingest
    - sample_key: per-task id (job_id/session_id) for gray percent bucketing :-)
    """
    trace = ExecutionTrace()
    bucket_key = sample_key or session_id

    # Master flag off OR gray/kill excludes this task → full legacy
    if not should_use_trusted_pipeline(
        user_id=user_id,
        tenant_id=tenant_id,
        sample_key=bucket_key,
        force=force_trusted_sample,
    ):
        with stage_span("legacy_write", reason="disabled_or_gray"):
            report, researcher = await legacy_full_runner()
        trace.mode = "disabled"
        trace.legacy_write = True
        trace.legacy_write_count = 1
        trace.legacy_write_reason = "disabled_full_path"
        return TrustOutcome(
            report=report if isinstance(report, str) else str(report),
            report_trust="legacy_unverified",
            citation_unverified=True,
            researcher=researcher,
            trusted_pipeline={"mode": "disabled", "execution_trace": trace.to_dict()},
        )

    # Shared gather (no report writing)
    with stage_span("research_only"):
        researcher, sources = await research_only_runner()
    trace.research_only = True
    if after_research is not None:
        maybe = after_research(researcher, sources)
        if hasattr(maybe, "__await__"):
            await maybe

    async def _trusted() -> tuple[str, dict[str, Any], AuditResult]:
        return await run_trusted_write_pipeline(
            question=question,
            report_type=report_type,
            tenant_id=tenant_id,
            session_id=session_id,
            user_id=user_id,
            writing_requirements=writing_requirements,
            session_summary=session_summary,
            checkpoint=checkpoint,
            save_checkpoint=save_checkpoint,
            llm_call=llm_call,
            retrieve_fn=retrieve_fn,
            document_map_entries=document_map_entries,
        )

    if trusted_report_shadow_mode():
        trace.mode = "shadow"
        import time

        t0 = time.time()
        with stage_span("legacy_write", reason="shadow"):
            legacy_report = await legacy_write_runner(researcher)
        legacy_ms = (time.time() - t0) * 1000
        trace.legacy_write = True
        trace.legacy_write_count = 1
        trace.legacy_write_reason = "shadow"
        shadow: Optional[dict[str, Any]] = None
        t1 = time.time()
        try:
            t_report, artifacts, audit = await _trusted()
            trusted_ms = (time.time() - t1) * 1000
            trace.trusted_write = True
            shadow = {
                "report": t_report,
                "artifacts": artifacts,
                "audit": audit.to_dict(),
                "report_trust_if_promoted": "trusted",
                "compare": shadow_compare(
                    legacy_report=legacy_report if isinstance(legacy_report, str) else str(legacy_report),
                    trusted_report=t_report,
                    legacy_ms=legacy_ms,
                    trusted_ms=trusted_ms,
                ),
            }
        except CitationAuditFailed as exc:
            trusted_ms = (time.time() - t1) * 1000
            trace.trusted_write = True
            t_report = exc.report or ""
            artifacts = exc.artifacts or {}
            audit = exc.audit or AuditResult(citation_audit_failed=True)
            logger.warning(
                "Trusted shadow audit failed (keeping draft for compare): coverage=%s",
                getattr(audit, "citation_coverage", None),
            )
            shadow = {
                "report": t_report,
                "artifacts": artifacts,
                "audit": audit.to_dict(),
                "error": "citation audit failed",
                "report_trust_if_promoted": "trusted",
                "compare": shadow_compare(
                    legacy_report=legacy_report if isinstance(legacy_report, str) else str(legacy_report),
                    trusted_report=t_report,
                    legacy_ms=legacy_ms,
                    trusted_ms=trusted_ms,
                ),
            }
        except Exception as exc:
            logger.warning("Trusted shadow failed (non-fatal): %s", exc)
            shadow = {"error": str(exc)[:500]}
        return TrustOutcome(
            report=legacy_report if isinstance(legacy_report, str) else str(legacy_report),
            report_trust="legacy_unverified",
            citation_unverified=True,
            researcher=researcher,
            trusted_shadow=shadow,
            trusted_pipeline={"mode": "shadow", "execution_trace": trace.to_dict()},
        )

    # Primary trusted path — must NOT call legacy write unless fallback
    trace.mode = "trusted_primary"
    try:
        t_report, artifacts, audit = await _trusted()
        trace.trusted_write = True
        artifacts = dict(artifacts)
        artifacts["execution_trace"] = trace.to_dict()
        record_release_anomaly(False)
        return TrustOutcome(
            report=t_report,
            report_trust="trusted",
            audit=audit,
            researcher=researcher,
            trusted_pipeline={"mode": "primary", **artifacts},
        )
    except CitationAuditFailed as exc:
        audit = exc.audit or AuditResult(citation_audit_failed=True)
        record_release_anomaly(True)
        if not trusted_report_fallback_to_legacy():
            trace.legacy_write = False
            return TrustOutcome(
                report="",
                report_trust="legacy_unverified",
                citation_audit_failed=True,
                citation_unverified=True,
                audit=audit,
                researcher=researcher,
                should_fail_job=True,
                error_code="citation_audit_failed",
                error_message=str(exc),
                trusted_pipeline={
                    "mode": "failed_no_fallback",
                    "audit": audit.to_dict(),
                    "draft": (checkpoint or {}).get("trusted", {}).get("synthesized"),
                    "execution_trace": trace.to_dict(),
                },
            )
        # Fallback: exactly one legacy write after trusted failure
        legacy_report = await legacy_write_runner(researcher)
        trace.legacy_write = True
        trace.legacy_write_count = 1
        trace.legacy_write_reason = "fallback"
        return TrustOutcome(
            report=legacy_report if isinstance(legacy_report, str) else str(legacy_report),
            report_trust="legacy_unverified",
            legacy_fallback=True,
            citation_unverified=True,
            citation_audit_failed=True,
            audit=audit,
            researcher=researcher,
            trusted_pipeline={
                "mode": "fallback_after_audit_fail",
                "audit": audit.to_dict(),
                "draft_cleared": True,
                "execution_trace": trace.to_dict(),
            },
        )
    except Exception as exc:
        logger.warning("Trusted pipeline error: %s", exc)
        if not trusted_report_fallback_to_legacy():
            return TrustOutcome(
                report="",
                report_trust="legacy_unverified",
                should_fail_job=True,
                error_code="trusted_pipeline_error",
                error_message=str(exc)[:500],
                citation_unverified=True,
                researcher=researcher,
                trusted_pipeline={
                    "mode": "failed_no_fallback",
                    "error": str(exc)[:500],
                    "execution_trace": trace.to_dict(),
                },
            )
        legacy_report = await legacy_write_runner(researcher)
        trace.legacy_write = True
        trace.legacy_write_count = 1
        trace.legacy_write_reason = "fallback"
        return TrustOutcome(
            report=legacy_report if isinstance(legacy_report, str) else str(legacy_report),
            report_trust="legacy_unverified",
            legacy_fallback=True,
            citation_unverified=True,
            researcher=researcher,
            error_message=str(exc)[:500],
            trusted_pipeline={
                "mode": "fallback_after_error",
                "error": str(exc)[:500],
                "execution_trace": trace.to_dict(),
            },
        )
