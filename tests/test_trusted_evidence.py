"""L2: Evidence quote verification and retrieve wiring."""

from __future__ import annotations

import asyncio
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


def test_quote_must_appear_in_chunk():
    from trusted_report.evidence import quote_in_source, verify_and_bind_evidence

    source = "The market grew 12% in 2024 according to IDC."
    assert quote_in_source("grew 12% in 2024", source)
    assert not quote_in_source("grew 99% in 2024", source)

    passages = [
        {
            "chunk_id": "c1",
            "parent_chunk_id": "p1",
            "document_id": "d1",
            "title": "IDC",
            "url": "https://example.com/idc",
            "page": 12,
            "content": source,
            "tenant_id": "t1",
            "session_id": "s1",
        }
    ]
    ok, cross = verify_and_bind_evidence(
        [
            {
                "evidence_id": "ev_001",
                "chunk_id": "c1",
                "quote": "grew 12% in 2024",
                "url": "https://example.com/idc",
                "page": 12,
            },
            {
                "evidence_id": "ev_bad",
                "chunk_id": "c1",
                "quote": "invented 50% growth",
            },
        ],
        passages,
        tenant_id="t1",
        session_id="s1",
    )
    assert len(ok) == 1
    assert ok[0].page == 12
    assert ok[0].url.endswith("/idc")
    assert ok[0].chunk_id == "c1"
    assert cross == 0


def test_cross_session_evidence_rejected():
    from trusted_report.evidence import verify_and_bind_evidence

    passages = [
        {
            "chunk_id": "c1",
            "parent_chunk_id": "p1",
            "document_id": "d1",
            "title": "X",
            "url": "u",
            "page": 1,
            "content": "exact quote text here about Redis",
            "tenant_id": "t1",
            "session_id": "other-session",
        }
    ]
    ok, cross = verify_and_bind_evidence(
        [{"evidence_id": "ev_001", "chunk_id": "c1", "quote": "exact quote text here about Redis"}],
        passages,
        tenant_id="t1",
        session_id="s1",
    )
    assert ok == []
    assert cross == 1


def test_extract_uses_retrieve_fn_not_per_chunk_summary():
    from trusted_report.evidence import extract_section_evidence
    from trusted_report.models import OutlineSection

    calls = {"retrieve": 0, "llm": 0}

    def retrieve_fn(query, **kwargs):
        calls["retrieve"] += 1
        return [
            SimpleNamespace(
                chunk_id="c1",
                parent_id="p1",
                document_id="d1",
                content="Redis supports persistence and replication features.",
                title="Redis",
                source_url="https://redis.io",
                page_number=3,
                tenant_id="t1",
                session_id="s1",
                token_estimate=20,
            )
        ]

    async def llm_call(messages):
        calls["llm"] += 1
        return json.dumps(
            {
                "evidence": [
                    {
                        "evidence_id": "ev_001",
                        "chunk_id": "c1",
                        "quote": "supports persistence and replication",
                        "url": "https://redis.io",
                        "page": 3,
                        "relevance": 0.9,
                    }
                ]
            }
        )

    section = OutlineSection(
        section_id="overview",
        title="Overview",
        search_queries=["Redis persistence"],
        questions_to_answer=["Does Redis persist?"],
    )
    items, cross, passages = asyncio.run(
        extract_section_evidence(
            section,
            tenant_id="t1",
            session_id="s1",
            retrieve_fn=retrieve_fn,
            llm_call=llm_call,
        )
    )
    assert calls["retrieve"] >= 1
    assert calls["llm"] == 1  # one evidence call, not per-chunk summarize loop
    assert len(items) == 1
    assert items[0].page == 3
    assert cross == 0
    assert passages[0]["chunk_id"] == "c1"
