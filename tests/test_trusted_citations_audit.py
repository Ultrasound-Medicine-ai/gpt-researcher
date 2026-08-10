"""L5: citation injection + audit failure semantics."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
for path in (ROOT, BACKEND):
    p = str(path)
    if p not in sys.path:
        sys.path.insert(0, p)


def _fixtures():
    from trusted_report.models import ClaimItem, EvidenceItem

    evidence = [
        EvidenceItem(
            evidence_id="ev_001",
            chunk_id="c1",
            parent_chunk_id="p1",
            quote="grew 12% in 2024",
            source_title="IDC",
            url="https://example.com/idc",
            page=12,
            document_id="d1",
            tenant_id="t1",
            session_id="s1",
        )
    ]
    claims = [
        ClaimItem(
            claim_id="cl_1",
            section_id="m",
            statement="Market grew 12% in 2024.",
            claim_type="fact",
            evidence_ids=["ev_001"],
            requires_citation=True,
            contains_number=True,
        )
    ]
    return claims, evidence


def test_inject_and_trace_to_chunk():
    from trusted_report.citations import inject_citations, trace_claim_to_source

    claims, evidence = _fixtures()
    body = "Market grew. [[claim:cl_1]]"
    final, nums = inject_citations(body, claims, evidence)
    assert "[1]" in final
    assert "[[claim:" not in final
    assert "p.12" in final or "12" in final
    assert "https://example.com/idc" in final
    trace = trace_claim_to_source("cl_1", claims, evidence)
    assert trace["chunks"][0]["chunk_id"] == "c1"
    assert trace["chunks"][0]["page"] == 12


def test_audit_fails_when_evidence_missing():
    from trusted_report.citations import audit_report
    from trusted_report.models import ClaimItem

    claims = [
        ClaimItem(
            claim_id="cl_1",
            section_id="m",
            statement="Market grew 12%.",
            evidence_ids=["ev_gone"],
            requires_citation=True,
            contains_number=True,
        )
    ]
    audit = audit_report("Market grew. [[claim:cl_1]]", claims, evidence=[])
    assert audit.citation_audit_failed is True
    assert "cl_1" in audit.unsupported_claims


def test_audit_pass_does_not_fail():
    from trusted_report.citations import audit_report

    claims, evidence = _fixtures()
    audit = audit_report("Market grew. [[claim:cl_1]]", claims, evidence)
    assert audit.citation_audit_failed is False
    assert audit.citation_coverage >= 0.85
