"""Fallback / shadow trust semantics — never mark fallback as trusted."""

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


def test_fallback_marks_legacy_unverified_not_trusted():
    from trusted_report.models import AuditResult, CitationAuditFailed
    from trusted_report.pipeline import apply_trust_policy

    async def boom(*args, **kwargs):
        raise CitationAuditFailed(
            "fail",
            audit=AuditResult(citation_audit_failed=True, unsupported_claims=["cl_x"]),
        )

    with patch.dict(
        os.environ,
        {
            "TRUSTED_REPORT_PIPELINE_ENABLED": "true",
            "TRUSTED_REPORT_SHADOW_MODE": "false",
            "TRUSTED_REPORT_FALLBACK_TO_LEGACY": "true",
        },
        clear=False,
    ), patch(
        "trusted_report.pipeline.run_trusted_write_pipeline",
        side_effect=boom,
    ):
        outcome = asyncio.run(
            apply_trust_policy(
                legacy_report="LEGACY REPORT BODY",
                question="q",
                report_type="research_report",
                tenant_id="t1",
                session_id="s1",
                user_id="u1",
            )
        )
    assert outcome.report == "LEGACY REPORT BODY"
    assert outcome.report_trust == "legacy_unverified"
    assert outcome.legacy_fallback is True
    assert outcome.citation_unverified is True
    assert outcome.report_trust != "trusted"
    meta = outcome.result_metadata()
    assert meta["report_trust"] == "legacy_unverified"


def test_no_fallback_fails_job_without_pseudo_trusted_report():
    from trusted_report.models import AuditResult, CitationAuditFailed
    from trusted_report.pipeline import apply_trust_policy

    async def boom(*args, **kwargs):
        raise CitationAuditFailed(
            "fail", audit=AuditResult(citation_audit_failed=True)
        )

    with patch.dict(
        os.environ,
        {
            "TRUSTED_REPORT_PIPELINE_ENABLED": "true",
            "TRUSTED_REPORT_SHADOW_MODE": "false",
            "TRUSTED_REPORT_FALLBACK_TO_LEGACY": "false",
        },
        clear=False,
    ), patch(
        "trusted_report.pipeline.run_trusted_write_pipeline",
        side_effect=boom,
    ):
        outcome = asyncio.run(
            apply_trust_policy(
                legacy_report="LEGACY SHOULD NOT BE DELIVERED",
                question="q",
                report_type="research_report",
                tenant_id="t1",
                session_id="s1",
                user_id="u1",
            )
        )
    assert outcome.should_fail_job is True
    assert outcome.error_code == "citation_audit_failed"
    assert outcome.report_trust != "trusted"
    assert outcome.report == ""


def test_shadow_delivers_legacy_trust():
    from trusted_report.pipeline import apply_trust_policy
    from trusted_report.models import AuditResult

    async def shadow_ok(*args, **kwargs):
        return "TRUSTED_DRAFT", {"outline": {}}, AuditResult(citation_audit_failed=False)

    with patch.dict(
        os.environ,
        {
            "TRUSTED_REPORT_PIPELINE_ENABLED": "true",
            "TRUSTED_REPORT_SHADOW_MODE": "true",
            "TRUSTED_REPORT_FALLBACK_TO_LEGACY": "true",
        },
        clear=False,
    ), patch(
        "trusted_report.pipeline.run_trusted_write_pipeline",
        side_effect=shadow_ok,
    ):
        outcome = asyncio.run(
            apply_trust_policy(
                legacy_report="LEGACY",
                researcher=SimpleNamespace(name="r"),
                question="q",
                report_type="research_report",
                tenant_id="t1",
                session_id="s1",
                user_id="u1",
            )
        )
    assert outcome.report == "LEGACY"
    assert outcome.report_trust == "legacy_unverified"
    assert outcome.trusted_shadow is not None
    assert outcome.trusted_shadow.get("report") == "TRUSTED_DRAFT"
