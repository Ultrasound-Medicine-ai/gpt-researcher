"""L4: Section writer markers + synthesis marker preservation."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
for path in (ROOT, BACKEND):
    p = str(path)
    if p not in sys.path:
        sys.path.insert(0, p)


def test_writer_ensures_claim_markers_for_facts():
    from trusted_report.models import ClaimItem, OutlineSection
    from trusted_report.writer import ensure_claim_markers, extract_claim_markers, write_section

    claims = [
        ClaimItem(
            claim_id="cl_market_001",
            section_id="market",
            statement="Cloud market grew in 2025.",
            claim_type="fact",
            evidence_ids=["ev_001"],
            contains_number=True,
        )
    ]
    # Model forgot markers
    body = ensure_claim_markers("Cloud market grew in 2025.", claims)
    assert "[[claim:cl_market_001]]" in body

    async def llm_call(messages):
        # Returns prose without markers and with forged [1]
        return "Cloud market grew in 2025. [1]"

    section = OutlineSection(section_id="market", title="Market", purpose="overview")
    text, warnings = asyncio.run(
        write_section(section, claims, llm_call=llm_call)
    )
    assert "[[claim:cl_market_001]]" in text
    assert "[1]" not in text or "[[claim:" in text
    assert extract_claim_markers(text)


def test_synthesis_preserves_claim_mapping():
    from trusted_report.models import ClaimItem, OutlineSection, ReportOutline
    from trusted_report.synthesis import preserve_claim_markers, synthesize_report

    original = (
        "## A\nGrew fast. [[claim:cl_a]]\n\n## B\nProfits fell. [[claim:cl_b]]"
    )
    bad = "## A\nGrew fast.\n\n## B\nProfits fell. However growth remains."
    fixed = preserve_claim_markers(original, bad)
    assert "[[claim:cl_a]]" in fixed
    assert "[[claim:cl_b]]" in fixed

    async def llm_call(messages):
        return bad

    outline = ReportOutline(
        report_thesis="t",
        sections=[
            OutlineSection(section_id="a", title="A"),
            OutlineSection(section_id="b", title="B"),
        ],
        cross_section_questions=["growth vs profit?"],
    )
    claims = [
        ClaimItem("cl_a", "a", "Grew fast.", evidence_ids=["e1"]),
        ClaimItem("cl_b", "b", "Profits fell.", evidence_ids=["e2"]),
    ]
    out = asyncio.run(
        synthesize_report(
            outline,
            {"a": "## A\nGrew fast. [[claim:cl_a]]", "b": "## B\nProfits fell. [[claim:cl_b]]"},
            claims,
            llm_call=llm_call,
        )
    )
    assert "[[claim:cl_a]]" in out and "[[claim:cl_b]]" in out
