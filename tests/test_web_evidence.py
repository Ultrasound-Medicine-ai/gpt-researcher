"""Unit tests for Web Evidence Pack helpers. :-)"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))


def test_web_evidence_helpers(monkeypatch):
    from rag import web_evidence as we

    monkeypatch.setenv("WEB_RAG_EVIDENCE_PACK", "true")
    monkeypatch.setenv("WEB_RAG_CONTEXT_BUDGET", "6000")
    assert we.web_evidence_pack_enabled() is True
    assert we.web_rag_context_budget_chars() == 6000

    monkeypatch.setenv("WEB_RAG_EVIDENCE_PACK", "false")
    assert we.web_evidence_pack_enabled() is False

    scope = we.rag_scope_from_headers(
        {
            "X-GPTR-Tenant-Id": "t1",
            "X-GPTR-User-Id": "u1",
            "X-GPTR-Session-Id": "11111111-1111-1111-1111-111111111111",
        }
    )
    assert scope["tenant_id"] == "t1"
    assert we.has_rag_scope(scope) is True
    assert we.has_rag_scope(
        {
            "X-GPTR-Tenant-Id": "t1",
            "X-GPTR-Session-Id": "11111111-1111-1111-1111-111111111111",
        }
    )
    assert we.has_rag_scope({"X-GPTR-Tenant-Id": "t1"}) is False

    preview = we.lightweight_scrape_preview(
        [
            {
                "url": "https://example.com/a",
                "title": "A",
                "raw_content": "x" * 1000,
            }
        ],
        max_chars=500,
    )
    assert "example.com" in preview
    assert len(preview) <= 600


def test_apply_pack_noop_without_scope(monkeypatch):
    from rag import web_evidence as we

    monkeypatch.setenv("WEB_RAG_EVIDENCE_PACK", "true")

    class R:
        headers = {}
        context = "old"
        research_sources = [{"url": "https://x", "raw_content": "y" * 80}]

        def get_research_sources(self):
            return self.research_sources

    r = R()
    import asyncio

    assert asyncio.run(we.apply_web_evidence_pack(r)) is False
    assert r.context == "old"
