"""Orchestrate trusted report stages with checkpoint resume."""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from trusted_report.citations import audit_report, inject_citations
from trusted_report.claims import build_section_claims
from trusted_report.document_map import build_document_map
from trusted_report.evidence import extract_section_evidence
from trusted_report.flags import (
    env_int,
    trusted_report_fallback_to_legacy,
    trusted_report_pipeline_enabled,
    trusted_report_shadow_mode,
)
from trusted_report.models import (
    AuditResult,
    CitationAuditFailed,
    ClaimItem,
    EvidenceItem,
    ReportOutline,
    TrustOutcome,
)
from trusted_report.eval import check_release_gates, evaluate_trusted_report
from trusted_report.planner import run_global_planner
from trusted_report.synthesis import synthesize_report
from trusted_report.tracing import pipeline_trace_scope, stage_span
from trusted_report.writer import write_section

logger = logging.getLogger(__name__)


def _cp_get(checkpoint: Optional[dict], *keys, default=None):
    node = (checkpoint or {}).get("trusted") or {}
    for k in keys:
        if not isinstance(node, dict):
            return default
        node = node.get(k)
    return default if node is None else node


async def run_trusted_write_pipeline(
    *,
    question: str,
    report_type: str,
    tenant_id: str,
    session_id: Optional[str],
    user_id: Optional[str] = None,
    writing_requirements: str = "",
    session_summary: str = "",
    checkpoint: Optional[dict[str, Any]] = None,
    save_checkpoint: Optional[Callable[[dict], Any]] = None,
    llm_call: Optional[Callable[..., Any]] = None,
    retrieve_fn: Optional[Callable[..., list]] = None,
    document_map_entries: Optional[list] = None,
) -> tuple[str, dict[str, Any], AuditResult]:
    """
    Run planner → evidence/claims → writer → synthesis → audit prep.
    Returns (report_with_markers, artifact_dict, audit_before_inject).
    Raises CitationAuditFailed if audit fails (caller decides fallback).
    """
    with pipeline_trace_scope() as tr:
        return await _run_trusted_write_pipeline_inner(
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
            pipeline_trace=tr,
        )


async def _run_trusted_write_pipeline_inner(
    *,
    question: str,
    report_type: str,
    tenant_id: str,
    session_id: Optional[str],
    user_id: Optional[str],
    writing_requirements: str,
    session_summary: str,
    checkpoint: Optional[dict[str, Any]],
    save_checkpoint: Optional[Callable[[dict], Any]],
    llm_call: Optional[Callable[..., Any]],
    retrieve_fn: Optional[Callable[..., list]],
    document_map_entries: Optional[list],
    pipeline_trace: Any,
) -> tuple[str, dict[str, Any], AuditResult]:
    trusted_cp: dict[str, Any] = dict((checkpoint or {}).get("trusted") or {})

    async def _save(stage: str, **extra):
        if save_checkpoint is None:
            return
        trusted_cp.update(extra)
        trusted_cp["stage"] = stage
        payload = dict(checkpoint or {})
        payload["trusted"] = trusted_cp
        result = save_checkpoint(payload)
        if hasattr(result, "__await__"):
            await result

    # Document map
    if document_map_entries is not None:
        doc_map = document_map_entries
    else:
        doc_map = build_document_map(
            tenant_id=tenant_id,
            session_id=session_id,
            research_id=session_id,
            user_id=user_id,
        )
    await _save("document_map", document_map=[d.to_dict() for d in doc_map])

    # Planner
    outline_data = trusted_cp.get("outline")
    if outline_data:
        outline = ReportOutline.from_dict(outline_data)
    else:
        with stage_span("planner", report_type=report_type):
            outline = await run_global_planner(
                question=question,
                report_type=report_type,
                writing_requirements=writing_requirements,
                document_map=doc_map,
                session_summary=session_summary,
                llm_call=llm_call,
            )
        await _save("planned", outline=outline.to_dict())

    sections_state: dict[str, Any] = dict(trusted_cp.get("sections") or {})
    section_bodies: dict[str, str] = {}
    cross_scope = 0
    warnings: list[str] = []
    prior: list[ClaimItem] = []

    for sec in outline.sections:
        st = dict(sections_state.get(sec.section_id) or {})
        if st.get("evidence") is not None and st.get("claims") is not None:
            claims = [ClaimItem.from_dict(c) for c in st["claims"]]
            cross_scope += int(st.get("cross_scope") or 0)
        else:
            with stage_span("evidence", section_id=sec.section_id):
                evid, cross, _passages = await extract_section_evidence(
                    sec,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    session_id=session_id,
                    retrieve_fn=retrieve_fn,
                    llm_call=llm_call,
                )
            cross_scope += cross
            with stage_span("claim", section_id=sec.section_id):
                claims, unsupported, cross2 = await build_section_claims(
                    sec,
                    evid,
                    tenant_id=tenant_id,
                    session_id=session_id,
                    llm_call=llm_call,
                )
            cross_scope += cross2
            if unsupported:
                warnings.append(f"unsupported_raw_claims:{unsupported}")
            st = {
                "evidence": [e.to_dict() for e in evid],
                "claims": [c.to_dict() for c in claims],
                "cross_scope": cross,
            }
            sections_state[sec.section_id] = st
            await _save("section_claims", sections=sections_state)

        body = st.get("draft")
        if not body:
            evid_for_writer = [
                EvidenceItem.from_dict(e) for e in (st.get("evidence") or [])
            ]
            with stage_span("writer", section_id=sec.section_id):
                body, w = await write_section(
                    sec,
                    claims,
                    prior_claims=prior,
                    evidence=evid_for_writer,
                    legacy_report_body=None,
                    llm_call=llm_call,
                )
            warnings.extend(w)
            st["draft"] = body
            sections_state[sec.section_id] = st
            await _save("section_draft", sections=sections_state)

        section_bodies[sec.section_id] = body or ""
        prior.extend(claims)

    all_evidence: list[EvidenceItem] = []
    all_claims: list[ClaimItem] = []
    for sec in outline.sections:
        st = sections_state.get(sec.section_id) or {}
        all_evidence.extend(EvidenceItem.from_dict(e) for e in (st.get("evidence") or []))
        all_claims.extend(ClaimItem.from_dict(c) for c in (st.get("claims") or []))
        section_bodies[sec.section_id] = st.get("draft") or section_bodies.get(sec.section_id, "")

    synthesized = trusted_cp.get("synthesized")
    if not synthesized:
        with stage_span("synthesis", sections=len(section_bodies)):
            synthesized = await synthesize_report(
                outline, section_bodies, all_claims, llm_call=llm_call
            )
        await _save("synthesized", synthesized=synthesized, sections=sections_state)

    min_cov = env_int("TRUSTED_MIN_CITATION_COVERAGE_PCT", 85, minimum=1) / 100.0
    with stage_span("audit"):
        audit = audit_report(
            synthesized,
            all_claims,
            all_evidence,
            cross_scope_violations=cross_scope,
            min_coverage=min_cov,
        )
        audit.warnings = warnings
        scores = evaluate_trusted_report(
            report_with_markers=synthesized,
            claims=all_claims,
            evidence=all_evidence,
            audit=audit,
        )
        gate = check_release_gates(
            audit=audit,
            scores=scores,
            duration_ms=pipeline_trace.to_dict().get("total_duration_ms"),
        )
        if not gate.passed and not audit.citation_audit_failed:
            # Soft eval failures still fail trust unless only warnings
            hard = [r for r in gate.reasons if not r.startswith("p95") and not r.startswith("cost")]
            if hard:
                audit.citation_audit_failed = True
                audit.warnings = list(audit.warnings or []) + [f"release_gate:{r}" for r in hard]

    artifacts = {
        "outline": outline.to_dict(),
        "sections": sections_state,
        "evidence": [e.to_dict() for e in all_evidence],
        "claims": [c.to_dict() for c in all_claims],
        "synthesized_markers": synthesized,
        "audit": audit.to_dict(),
        "eval_scores": scores.to_dict(),
        "release_gate": gate.to_dict(),
        "trace": pipeline_trace.to_dict(),
    }
    await _save(
        "audited",
        audit=artifacts["audit"],
        synthesized=synthesized,
        eval_scores=artifacts["eval_scores"],
        trace=artifacts["trace"],
    )

    final_report, _nums = inject_citations(synthesized, all_claims, all_evidence)
    artifacts["report"] = final_report
    await _save("citations_injected", report=final_report)

    if audit.citation_audit_failed:
        # Keep draft+citations for shadow compare; primary path still fails. :-)
        raise CitationAuditFailed(
            "citation audit failed",
            audit=audit,
            report=final_report,
            artifacts=artifacts,
        )
    return final_report, artifacts, audit


async def apply_trust_policy(
    *,
    legacy_report: str,
    researcher: Any = None,
    question: str,
    report_type: str,
    tenant_id: str,
    session_id: Optional[str],
    user_id: Optional[str],
    writing_requirements: str = "",
    session_summary: str = "",
    checkpoint: Optional[dict[str, Any]] = None,
    save_checkpoint: Optional[Callable[[dict], Any]] = None,
    llm_call: Optional[Callable[..., Any]] = None,
    retrieve_fn: Optional[Callable[..., list]] = None,
    document_map_entries: Optional[list] = None,
) -> TrustOutcome:
    """
    Apply trusted / shadow / fallback policy AFTER legacy research+draft exists.

    Uses the precomputed legacy_report for fallback (no second run_agent).
    Never persists — caller persists once.
    """
    legacy_text = legacy_report if isinstance(legacy_report, str) else str(legacy_report)

    if not trusted_report_pipeline_enabled():
        return TrustOutcome(
            report=legacy_text,
            report_trust="legacy_unverified",
            citation_unverified=True,
            researcher=researcher,
            trusted_pipeline={"mode": "disabled"},
        )

    if trusted_report_shadow_mode():
        shadow: Optional[dict[str, Any]] = None
        try:
            t_report, artifacts, audit = await run_trusted_write_pipeline(
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
            shadow = {
                "report": t_report,
                "artifacts": artifacts,
                "audit": audit.to_dict(),
                "report_trust_if_promoted": "trusted",
            }
        except Exception as exc:
            logger.warning("Trusted shadow failed (non-fatal): %s", exc)
            shadow = {"error": str(exc)[:500]}
        return TrustOutcome(
            report=legacy_text,
            report_trust="legacy_unverified",
            citation_unverified=True,
            researcher=researcher,
            trusted_shadow=shadow,
            trusted_pipeline={"mode": "shadow"},
        )

    try:
        t_report, artifacts, audit = await run_trusted_write_pipeline(
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
        return TrustOutcome(
            report=t_report,
            report_trust="trusted",
            audit=audit,
            researcher=researcher,
            trusted_pipeline={"mode": "primary", **artifacts},
        )
    except CitationAuditFailed as exc:
        audit = exc.audit or AuditResult(citation_audit_failed=True)
        if trusted_report_fallback_to_legacy():
            return TrustOutcome(
                report=legacy_text,
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
                },
            )
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
            },
        )
    except Exception as exc:
        logger.warning("Trusted pipeline error: %s", exc)
        if trusted_report_fallback_to_legacy():
            return TrustOutcome(
                report=legacy_text,
                report_trust="legacy_unverified",
                legacy_fallback=True,
                citation_unverified=True,
                researcher=researcher,
                error_message=str(exc)[:500],
                trusted_pipeline={"mode": "fallback_after_error", "error": str(exc)[:500]},
            )
        return TrustOutcome(
            report="",
            report_trust="legacy_unverified",
            should_fail_job=True,
            error_code="trusted_pipeline_error",
            error_message=str(exc)[:500],
            citation_unverified=True,
            researcher=researcher,
            trusted_pipeline={"mode": "failed_no_fallback", "error": str(exc)[:500]},
        )


async def deliver_with_policy(
    *,
    question: str,
    report_type: str,
    tenant_id: str,
    session_id: Optional[str],
    user_id: Optional[str],
    legacy_runner: Callable[..., Any],
    writing_requirements: str = "",
    session_summary: str = "",
    checkpoint: Optional[dict[str, Any]] = None,
    save_checkpoint: Optional[Callable[[dict], Any]] = None,
    llm_call: Optional[Callable[..., Any]] = None,
    retrieve_fn: Optional[Callable[..., list]] = None,
    document_map_entries: Optional[list] = None,
) -> TrustOutcome:
    """Run legacy_runner once, then apply_trust_policy (for tests / alternate callers)."""
    report, researcher = await legacy_runner()
    return await apply_trust_policy(
        legacy_report=report if isinstance(report, str) else str(report),
        researcher=researcher,
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
