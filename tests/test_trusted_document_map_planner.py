"""L1: document map + planner input boundaries (no per-chunk LLM summary)."""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
for path in (ROOT, BACKEND):
    p = str(path)
    if p not in sys.path:
        sys.path.insert(0, p)


def _load_pkg():
    # Ensure package imports resolve
    import trusted_report.document_map as document_map
    import trusted_report.planner as planner
    import trusted_report.models as models

    return document_map, planner, models


def test_document_map_truncates_excerpt_without_llm():
    document_map, _, _ = _load_pkg()
    long = "A" * 2000
    rows = [
        {
            "document_id": "d1",
            "parent_chunk_id": "p1",
            "title": "Doc",
            "heading": "Intro",
            "content": long,
            "source_type": "upload",
            "child_count": 3,
        }
    ]
    entries = document_map.build_document_map_from_rows(rows)
    assert len(entries) == 1
    assert entries[0].sections[0].child_count == 3
    assert len(entries[0].sections[0].summary_or_excerpt) < 400
    assert "A" * 500 not in entries[0].sections[0].summary_or_excerpt


def test_planner_payload_excludes_child_full_text():
    document_map, planner, models = _load_pkg()
    entries = [
        models.DocumentMapEntry(
            document_id="d1",
            title="T",
            source_type="report",
            sections=[
                models.MapSection(
                    parent_chunk_id="p1",
                    heading="H",
                    position=1,
                    summary_or_excerpt="short parent excerpt",
                    child_count=5,
                )
            ],
        )
    ]
    payload = planner.planner_input_payload(
        question="What is Redis?",
        report_type="research_report",
        writing_requirements="concise",
        document_map=entries,
        session_summary="user asked about Redis",
    )
    assert payload["includes_child_full_text"] is False
    dumped = json.dumps(payload["document_map"])
    assert "short parent excerpt" in dumped
    assert "CHILD_FULL_TEXT_SHOULD_NOT_APPEAR" not in dumped


def test_planner_parses_strict_json_via_mock_llm():
    _, planner, _ = _load_pkg()

    async def fake_llm(messages):
        return json.dumps(
            {
                "report_thesis": "Redis vs Memcached",
                "scope": "comparison",
                "time_range": "2020-2025",
                "sections": [
                    {
                        "section_id": "overview",
                        "title": "Overview",
                        "purpose": "define terms",
                        "questions_to_answer": ["What is Redis?"],
                        "search_queries": ["Redis overview"],
                        "expected_claim_types": ["fact"],
                    }
                ],
                "cross_section_questions": ["Are definitions consistent?"],
            }
        )

    outline = asyncio.run(
        planner.run_global_planner(
            question="compare",
            document_map=[],
            llm_call=fake_llm,
        )
    )
    assert outline.sections[0].section_id == "overview"
    assert outline.report_thesis
