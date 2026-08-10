"""Smoke checks for trusted report policy (mock LLM; no live research).

  python scripts/e2e_trusted_report_pipeline.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))


def _ok(name: str) -> None:
    print(f"PASS: {name}")


def _fail(name: str, detail: str) -> None:
    print(f"FAIL: {name} — {detail}")
    raise SystemExit(1)


async def main_async() -> int:
    from trusted_report.document_map import build_document_map_from_rows
    from trusted_report.models import (
        AuditResult,
        CitationAuditFailed,
        ClaimItem,
        DocumentMapEntry,
        EvidenceItem,
        MapSection,
        OutlineSection,
        ReportOutline,
    )
    from trusted_report.execution import execute_report_job
    from trusted_report.pipeline import run_trusted_write_pipeline
    from trusted_report.citations import inject_citations, audit_report
    from trusted_report.planner import planner_input_payload
    from trusted_report.gray import clear_kill_switch

    clear_kill_switch()

    # 1) No per-chunk LLM in document map
    entries = build_document_map_from_rows(
        [
            {
                "document_id": "d1",
                "parent_chunk_id": "p1",
                "heading": "Intro",
                "content": "Parent excerpt only " * 20,
                "source_type": "upload",
                "child_count": 4,
            }
        ]
    )
    payload = planner_input_payload(
        question="q",
        report_type="research_report",
        writing_requirements="",
        document_map=entries,
    )
    if payload["includes_child_full_text"]:
        _fail("no_chunk_summary", "planner payload claims child full text")
    _ok("document_map_no_per_chunk_llm")

    # 2) Disabled → legacy full only
    async def legacy_full():
        return "LEGACY", SimpleNamespace(name="r")

    async def research_only():
        raise AssertionError("research_only should not run when disabled")

    async def legacy_write(r):
        raise AssertionError("legacy_write should not run when disabled")

    with patch.dict(
        os.environ,
        {
            "TRUSTED_REPORT_PIPELINE_ENABLED": "false",
            "TRUSTED_REPORT_GRAY_PERCENT": "100",
        },
        clear=False,
    ):
        out = await execute_report_job(
            question="q",
            report_type="research_report",
            tenant_id="t",
            session_id="s",
            user_id="u",
            research_only_runner=research_only,
            legacy_full_runner=legacy_full,
            legacy_write_runner=legacy_write,
        )
    if out.report_trust != "legacy_unverified" or out.report != "LEGACY":
        _fail("flag_off", str(out.result_metadata()))
    _ok("flag_off_legacy_unverified")

    # 3) Fallback: trusted fails → exactly one legacy_write (not pre-generated body)
    counters = {"lw": 0}

    async def research_only_ok():
        return SimpleNamespace(name="r"), []

    async def legacy_write_fb(r):
        counters["lw"] += 1
        return "LEGACY_FB"

    async def boom(*a, **k):
        raise CitationAuditFailed("x", audit=AuditResult(citation_audit_failed=True))

    with patch.dict(
        os.environ,
        {
            "TRUSTED_REPORT_PIPELINE_ENABLED": "true",
            "TRUSTED_REPORT_SHADOW_MODE": "false",
            "TRUSTED_REPORT_FALLBACK_TO_LEGACY": "true",
            "TRUSTED_REPORT_GRAY_PERCENT": "100",
        },
        clear=False,
    ), patch(
        "trusted_report.execution.run_trusted_write_pipeline",
        side_effect=boom,
    ):
        out = await execute_report_job(
            question="q",
            report_type="research_report",
            tenant_id="t",
            session_id="s",
            user_id="u",
            research_only_runner=research_only_ok,
            legacy_full_runner=legacy_full,
            legacy_write_runner=legacy_write_fb,
        )
    if out.report_trust == "trusted" or not out.legacy_fallback:
        _fail("fallback_trust", str(out.result_metadata()))
    if out.report != "LEGACY_FB" or counters["lw"] != 1:
        _fail("fallback_body", f"{out.report} lw={counters['lw']}")
    _ok("fallback_legacy_unverified")

    # 4) Traceability inject
    claims = [
        ClaimItem(
            claim_id="cl_1",
            section_id="m",
            statement="Grew 12%.",
            evidence_ids=["ev_1"],
            requires_citation=True,
            contains_number=True,
        )
    ]
    evidence = [
        EvidenceItem(
            evidence_id="ev_1",
            chunk_id="c1",
            quote="grew 12%",
            url="https://ex.com",
            page=2,
            source_title="S",
        )
    ]
    final, _ = inject_citations("Grew. [[claim:cl_1]]", claims, evidence)
    audit = audit_report("Grew. [[claim:cl_1]]", claims, evidence)
    if "[1]" not in final or audit.citation_audit_failed:
        _fail("citations", final)
    _ok("citation_trace")

    # 5) End-to-end write with mocks (FTS path via retrieve_fn)
    outline_json = {
        "report_thesis": "t",
        "scope": "s",
        "sections": [
            {
                "section_id": "overview",
                "title": "Overview",
                "questions_to_answer": ["What?"],
                "search_queries": ["Redis"],
                "expected_claim_types": ["fact"],
            }
        ],
        "cross_section_questions": [],
    }

    async def llm_call(messages):
        user = messages[-1]["content"]
        if "Document map" in user or "report_thesis" in messages[0]["content"]:
            # planner / generic
            if "Return JSON with keys: report_thesis" in user:
                return json.dumps(outline_json)
        if "Candidate Child passages" in user:
            return json.dumps(
                {
                    "evidence": [
                        {
                            "evidence_id": "ev_001",
                            "chunk_id": "c1",
                            "quote": "Redis supports persistence",
                            "url": "https://redis.io",
                            "page": 1,
                            "relevance": 0.9,
                        }
                    ]
                }
            )
        if "Verified claims for this section" in user or "Claim Builder" in messages[0]["content"]:
            if "evidence_ids" in messages[0]["content"] or "Claim Builder" in messages[0]["content"]:
                return json.dumps(
                    {
                        "claims": [
                            {
                                "claim_id": "cl_overview_001",
                                "section_id": "overview",
                                "statement": "Redis supports persistence.",
                                "claim_type": "fact",
                                "evidence_ids": ["ev_001"],
                                "requires_citation": True,
                            }
                        ]
                    }
                )
        if "Section blueprint" in user:
            return "Redis supports persistence. [[claim:cl_overview_001]]"
        if "Global outline" in user:
            return "## Overview\nRedis supports persistence. [[claim:cl_overview_001]]"
        # default planner
        return json.dumps(outline_json)

    def retrieve_fn(query, **kwargs):
        return [
            SimpleNamespace(
                chunk_id="c1",
                parent_id="p1",
                document_id="d1",
                content="Redis supports persistence and replication in production.",
                title="Redis",
                source_url="https://redis.io",
                page_number=1,
                tenant_id="t",
                session_id="s",
                token_estimate=30,
            )
        ]

    with patch.dict(
        os.environ,
        {
            "TRUSTED_REPORT_PIPELINE_ENABLED": "true",
            "TRUSTED_REPORT_SHADOW_MODE": "false",
            "TRUSTED_MIN_CITATION_COVERAGE_PCT": "50",
        },
        clear=False,
    ):
        report, artifacts, audit = await run_trusted_write_pipeline(
            question="Redis persistence?",
            report_type="research_report",
            tenant_id="t",
            session_id="s",
            user_id="u",
            llm_call=llm_call,
            retrieve_fn=retrieve_fn,
            document_map_entries=entries,
        )
    if audit.citation_audit_failed:
        _fail("e2e_audit", audit.to_dict())
    if "[1]" not in report and "redis.io" not in report.lower():
        _fail("e2e_report", report[:200])
    _ok("mocked_trusted_pipeline")

    print("\nALL TRUSTED REPORT E2E CHECKS PASSED")
    return 0


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    raise SystemExit(main())
