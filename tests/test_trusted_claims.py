"""L3: Claim validation gates."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
for path in (ROOT, BACKEND):
    p = str(path)
    if p not in sys.path:
        sys.path.insert(0, p)


def _ev(**kwargs):
    from trusted_report.models import EvidenceItem

    base = dict(
        evidence_id="ev_001",
        chunk_id="c1",
        quote="Market size reached 100 billion in 2024",
        document_id="d1",
        url="https://a.example",
        tenant_id="t1",
        session_id="s1",
    )
    base.update(kwargs)
    return EvidenceItem(**base)


def test_claim_rejected_when_evidence_deleted():
    from trusted_report.claims import validate_claims

    claims, unsupported, cross = validate_claims(
        [
            {
                "claim_id": "cl_1",
                "statement": "Market size reached 100 billion in 2024",
                "claim_type": "fact",
                "evidence_ids": ["ev_001"],
                "contains_number": True,
            }
        ],
        evidence=[],  # deleted
        section_id="market",
        tenant_id="t1",
        session_id="s1",
    )
    assert unsupported == ["cl_1"]
    assert claims == []
    assert cross == 0


def test_cross_tenant_binding_rejected():
    from trusted_report.claims import validate_claims

    claims, unsupported, cross = validate_claims(
        [
            {
                "claim_id": "cl_1",
                "statement": "Market size reached 100 billion in 2024",
                "claim_type": "fact",
                "evidence_ids": ["ev_001"],
                "contains_number": True,
            }
        ],
        evidence=[_ev(tenant_id="other-tenant")],
        section_id="market",
        tenant_id="t1",
        session_id="s1",
    )
    assert cross >= 1
    assert "cl_1" in unsupported or not claims


def test_single_source_numeric_flagged():
    from trusted_report.claims import validate_claims

    claims, unsupported, _ = validate_claims(
        [
            {
                "claim_id": "cl_1",
                "statement": "Market size reached 100 billion in 2024",
                "claim_type": "fact",
                "evidence_ids": ["ev_001"],
                "contains_number": True,
            }
        ],
        evidence=[_ev()],
        section_id="market",
        tenant_id="t1",
        session_id="s1",
    )
    assert len(claims) == 1
    assert claims[0].single_source is True
    assert unsupported == []
