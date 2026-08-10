"""Authenticity gates: trusted path is Planner→Evidence→Claim→Writer, not legacy wrap."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
for path in (ROOT, BACKEND):
    p = str(path)
    if p not in sys.path:
        sys.path.insert(0, p)


def test_primary_trusted_does_not_call_legacy_write():
    from trusted_report.execution import execute_report_job
    from trusted_report.gray import clear_kill_switch
    from trusted_report.models import AuditResult

    clear_kill_switch()
    counters = {"research": 0, "legacy_full": 0, "legacy_write": 0, "trusted": 0}

    async def research_only():
        counters["research"] += 1
        return SimpleNamespace(name="r"), [{"url": "https://a", "excerpt": "x" * 50}]

    async def legacy_full():
        counters["legacy_full"] += 1
        return "SHOULD_NOT_RUN", None

    async def legacy_write(researcher):
        counters["legacy_write"] += 1
        return "LEGACY_BODY"

    async def trusted_ok(*a, **k):
        counters["trusted"] += 1
        return "TRUSTED_BODY", {"outline": {}}, AuditResult(citation_audit_failed=False)

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
        side_effect=trusted_ok,
    ):
        out = asyncio.run(
            execute_report_job(
                question="q",
                report_type="research_report",
                tenant_id="t",
                session_id="s",
                user_id="u",
                research_only_runner=research_only,
                legacy_full_runner=legacy_full,
                legacy_write_runner=legacy_write,
            )
        )
    assert out.report_trust == "trusted"
    assert out.report == "TRUSTED_BODY"
    assert counters["research"] == 1
    assert counters["trusted"] == 1
    assert counters["legacy_write"] == 0
    assert counters["legacy_full"] == 0
    trace = out.trusted_pipeline["execution_trace"]
    assert trace["legacy_write"] is False
    assert trace["legacy_write_count"] == 0
    assert trace["used_legacy_body_as_claim_source"] is False


def test_fallback_runs_legacy_write_exactly_once_after_trusted_fail():
    from trusted_report.execution import execute_report_job
    from trusted_report.models import AuditResult, CitationAuditFailed

    counters = {"legacy_write": 0, "trusted": 0}

    async def research_only():
        return SimpleNamespace(name="r"), []

    async def legacy_full():
        raise AssertionError("full path not for fallback")

    async def legacy_write(researcher):
        counters["legacy_write"] += 1
        return "LEGACY_AFTER_FAIL"

    async def boom(*a, **k):
        counters["trusted"] += 1
        raise CitationAuditFailed("fail", audit=AuditResult(citation_audit_failed=True))

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
        out = asyncio.run(
            execute_report_job(
                question="q",
                report_type="research_report",
                tenant_id="t",
                session_id="s",
                user_id="u",
                research_only_runner=research_only,
                legacy_full_runner=legacy_full,
                legacy_write_runner=legacy_write,
            )
        )
    assert counters["trusted"] == 1
    assert counters["legacy_write"] == 1
    assert out.legacy_fallback is True
    assert out.report_trust == "legacy_unverified"
    assert out.report == "LEGACY_AFTER_FAIL"
    assert out.trusted_pipeline["execution_trace"]["legacy_write_reason"] == "fallback"


def test_shadow_runs_both_but_delivers_legacy():
    from trusted_report.execution import execute_report_job
    from trusted_report.gray import clear_kill_switch
    from trusted_report.models import AuditResult

    clear_kill_switch()
    counters = {"legacy_write": 0, "trusted": 0}

    async def research_only():
        return SimpleNamespace(name="r"), []

    async def legacy_full():
        raise AssertionError("shadow should use research_only + legacy_write")

    async def legacy_write(researcher):
        counters["legacy_write"] += 1
        return "LEGACY_SHADOW"

    async def trusted_ok(*a, **k):
        counters["trusted"] += 1
        return "TRUSTED_SHADOW", {"outline": {}}, AuditResult(citation_audit_failed=False)

    with patch.dict(
        os.environ,
        {
            "TRUSTED_REPORT_PIPELINE_ENABLED": "true",
            "TRUSTED_REPORT_SHADOW_MODE": "true",
            "TRUSTED_REPORT_FALLBACK_TO_LEGACY": "true",
            "TRUSTED_REPORT_GRAY_PERCENT": "100",
        },
        clear=False,
    ), patch(
        "trusted_report.execution.run_trusted_write_pipeline",
        side_effect=trusted_ok,
    ):
        out = asyncio.run(
            execute_report_job(
                question="q",
                report_type="research_report",
                tenant_id="t",
                session_id="s",
                user_id="u",
                research_only_runner=research_only,
                legacy_full_runner=legacy_full,
                legacy_write_runner=legacy_write,
            )
        )
    assert counters["legacy_write"] == 1 and counters["trusted"] == 1
    assert out.report == "LEGACY_SHADOW"
    assert out.report_trust == "legacy_unverified"
    assert out.trusted_shadow["report"] == "TRUSTED_SHADOW"


def test_writer_rejects_legacy_report_body_and_unverified_claims():
    from trusted_report.models import ClaimItem, OutlineSection
    from trusted_report.writer import assert_writer_inputs_are_verified, write_section

    claims = [
        ClaimItem(
            claim_id="cl_1",
            section_id="s",
            statement="Grew 12%.",
            evidence_ids=["ev_1"],
            requires_citation=True,
        )
    ]
    try:
        assert_writer_inputs_are_verified(claims, legacy_report_body="# Legacy report")
        raised = False
    except ValueError:
        raised = True
    assert raised

    bad = [
        ClaimItem(
            claim_id="cl_bad",
            section_id="s",
            statement="Invented fact 99%.",
            evidence_ids=[],
            requires_citation=True,
            claim_type="fact",
        )
    ]
    accepted = assert_writer_inputs_are_verified(bad)
    assert accepted == []

    async def llm_call(messages):
        # Must not see legacy prose
        blob = json.dumps(messages)
        assert "LEGACY_FULL_REPORT" not in blob
        return "Grew 12%. [[claim:cl_1]]"

    text, _ = asyncio.run(
        write_section(
            OutlineSection(section_id="s", title="S"),
            claims,
            evidence=[SimpleNamespace(evidence_id="ev_1")],
            legacy_report_body=None,
            llm_call=llm_call,
        )
    )
    assert "[[claim:cl_1]]" in text


def test_citation_traces_to_child_chunk_quote():
    from trusted_report.citations import inject_citations, trace_claim_to_source
    from trusted_report.evidence import quote_in_source
    from trusted_report.models import ClaimItem, EvidenceItem

    chunk_text = "The market grew 12% in 2024 according to IDC."
    evidence = [
        EvidenceItem(
            evidence_id="ev_1",
            chunk_id="child-uuid-1",
            parent_chunk_id="parent-1",
            quote="grew 12% in 2024",
            url="https://example.com/idc",
            page=12,
            document_id="doc-1",
        )
    ]
    assert quote_in_source(evidence[0].quote, chunk_text)
    claims = [
        ClaimItem(
            claim_id="cl_1",
            section_id="m",
            statement="Market grew 12% in 2024.",
            evidence_ids=["ev_1"],
            requires_citation=True,
            contains_number=True,
        )
    ]
    final, nums = inject_citations("Market grew. [[claim:cl_1]]", claims, evidence)
    assert "[1]" in final
    trace = trace_claim_to_source("cl_1", claims, evidence)
    assert trace["chunks"][0]["chunk_id"] == "child-uuid-1"
    assert quote_in_source(trace["chunks"][0]["quote"], chunk_text)


def test_trusted_not_derived_from_legacy_body_in_pipeline_inputs():
    """Planner/evidence prompts must not include a legacy report body field."""
    from trusted_report.planner import planner_input_payload
    from trusted_report.models import DocumentMapEntry, MapSection
    from trusted_report import prompts

    payload = planner_input_payload(
        question="q",
        report_type="research_report",
        writing_requirements="",
        document_map=[
            DocumentMapEntry(
                document_id="d",
                title="t",
                sections=[
                    MapSection("p1", "H", 1, "excerpt", 2),
                ],
            )
        ],
    )
    assert "legacy_report" not in payload
    user = prompts.planner_user(
        question="q",
        report_type="research_report",
        writing_requirements="",
        document_map=payload["document_map"],
        session_summary="",
        token_budget=1000,
    )
    assert "legacy report" not in user.lower()
    assert "write_report" not in user.lower()
