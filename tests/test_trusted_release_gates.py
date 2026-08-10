"""Step 11: release gates, eval metrics, gray rollout, kill-switch."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
for path in (ROOT, BACKEND):
    p = str(path)
    if p not in sys.path:
        sys.path.insert(0, p)


def test_eval_and_release_gate_pass():
    from trusted_report.eval import check_release_gates, evaluate_trusted_report
    from trusted_report.models import AuditResult, ClaimItem, EvidenceItem

    evidence = [
        EvidenceItem(
            evidence_id="ev_1",
            chunk_id="c1",
            quote="grew 12% in 2024",
            url="https://ex.com",
            page=1,
        )
    ]
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
    audit = AuditResult(
        citation_coverage=1.0,
        total_claims=1,
        supported_claims=1,
        citation_audit_failed=False,
    )
    scores = evaluate_trusted_report(
        report_with_markers="Market grew. [[claim:cl_1]]",
        claims=claims,
        evidence=evidence,
        audit=audit,
        chunk_texts={"c1": "The market grew 12% in 2024 according to IDC."},
    )
    assert scores.citation_accuracy == 1.0
    assert scores.claim_support_rate == 1.0
    gate = check_release_gates(audit=audit, scores=scores, duration_ms=1000)
    assert gate.passed


def test_release_gate_fails_on_audit():
    from trusted_report.eval import check_release_gates, evaluate_trusted_report
    from trusted_report.models import AuditResult

    audit = AuditResult(citation_coverage=0.2, citation_audit_failed=True)
    scores = evaluate_trusted_report(
        report_with_markers="",
        claims=[],
        evidence=[],
        audit=audit,
    )
    gate = check_release_gates(audit=audit, scores=scores)
    assert not gate.passed
    assert "audit_failed" in gate.reasons


def test_gray_percent_and_kill_switch():
    from trusted_report import gray

    gray.clear_kill_switch()
    with patch.dict(
        os.environ,
        {
            "TRUSTED_REPORT_PIPELINE_ENABLED": "true",
            "TRUSTED_REPORT_SHADOW_MODE": "false",
            "TRUSTED_REPORT_GRAY_PERCENT": "0",
        },
        clear=False,
    ):
        assert gray.should_use_trusted_pipeline(user_id="u1", tenant_id="t1") is False

    with patch.dict(
        os.environ,
        {
            "TRUSTED_REPORT_PIPELINE_ENABLED": "true",
            "TRUSTED_REPORT_SHADOW_MODE": "false",
            "TRUSTED_REPORT_GRAY_PERCENT": "100",
        },
        clear=False,
    ):
        assert gray.should_use_trusted_pipeline(user_id="u1", tenant_id="t1") is True

    gray.activate_kill_switch("test", minutes=10)
    with patch.dict(
        os.environ,
        {
            "TRUSTED_REPORT_PIPELINE_ENABLED": "true",
            "TRUSTED_REPORT_GRAY_PERCENT": "100",
        },
        clear=False,
    ):
        assert gray.should_use_trusted_pipeline(user_id="u1", tenant_id="t1") is False
    gray.clear_kill_switch()


def test_shadow_also_respects_gray_percent():
    """Shadow is a dual-write runway, not 100% of enabled traffic. :-)"""
    from trusted_report import gray

    gray.clear_kill_switch()
    with patch.dict(
        os.environ,
        {
            "TRUSTED_REPORT_PIPELINE_ENABLED": "true",
            "TRUSTED_REPORT_SHADOW_MODE": "true",
            "TRUSTED_REPORT_GRAY_PERCENT": "0",
        },
        clear=False,
    ):
        assert (
            gray.should_use_trusted_pipeline(
                user_id="u1", tenant_id="t1", sample_key="job-a"
            )
            is False
        )

    with patch.dict(
        os.environ,
        {
            "TRUSTED_REPORT_PIPELINE_ENABLED": "true",
            "TRUSTED_REPORT_SHADOW_MODE": "true",
            "TRUSTED_REPORT_GRAY_PERCENT": "100",
        },
        clear=False,
    ):
        assert (
            gray.should_use_trusted_pipeline(
                user_id="u1", tenant_id="t1", sample_key="job-a"
            )
            is True
        )


def test_parse_relevance_accepts_chinese_labels():
    from trusted_report.evidence import parse_relevance

    assert parse_relevance("直接相关") == 1.0
    assert parse_relevance(0.8) == 0.8
    assert parse_relevance("not-a-score") == 0.0


def test_as_str_list_tolerates_bool():
    from trusted_report.models import as_str_list

    assert as_str_list(True) == []
    assert as_str_list(False) == []
    assert as_str_list(["a", 1]) == ["a", "1"]


def test_force_sample_bypasses_gray_when_allowed():
    from trusted_report import gray

    gray.clear_kill_switch()
    with patch.dict(
        os.environ,
        {
            "TRUSTED_REPORT_PIPELINE_ENABLED": "true",
            "TRUSTED_REPORT_SHADOW_MODE": "true",
            "TRUSTED_REPORT_GRAY_PERCENT": "0",
            "TRUSTED_REPORT_ALLOW_FORCE_SAMPLE": "true",
        },
        clear=False,
    ):
        assert (
            gray.should_use_trusted_pipeline(
                user_id="u1", tenant_id="t1", sample_key="job-x", force=True
            )
            is True
        )
        assert (
            gray.should_use_trusted_pipeline(
                user_id="u1", tenant_id="t1", sample_key="job-x", force=False
            )
            is False
        )


def test_gray_buckets_by_sample_key_not_anonymous_collapse():
    from trusted_report import gray

    gray.clear_kill_switch()
    with patch.dict(
        os.environ,
        {
            "TRUSTED_REPORT_PIPELINE_ENABLED": "true",
            "TRUSTED_REPORT_SHADOW_MODE": "true",
            "TRUSTED_REPORT_GRAY_PERCENT": "5",
        },
        clear=False,
    ):
        hits = sum(
            1
            for i in range(200)
            if gray.should_use_trusted_pipeline(
                user_id="anonymous",
                tenant_id="anonymous",
                sample_key=f"job-{i}",
            )
        )
        # ~5% of 200 ≈ 10; allow wide band for hash variance. :-)
        assert 2 <= hits <= 30


def test_anomaly_streak_trips_kill_switch():
    from trusted_report import gray

    gray.clear_kill_switch()
    with patch.dict(os.environ, {"TRUSTED_REPORT_ANOMALY_STREAK": "2"}, clear=False):
        gray.record_release_anomaly(True)
        assert not gray.kill_switch_active()
        gray.record_release_anomaly(True)
        assert gray.kill_switch_active()
    gray.clear_kill_switch()


def test_shadow_compare_reports_deltas():
    from trusted_report.eval import shadow_compare

    cmp = shadow_compare(
        legacy_report="Legacy body with [1]",
        trusted_report="Trusted body with [1][2]",
        legacy_ms=1000,
        trusted_ms=1500,
        legacy_cost=2,
        trusted_cost=3,
    )
    assert cmp["latency_delta_ms"] == 500
    assert cmp["cost_delta"] == 1
    assert cmp["trusted_has_citations"] is True
