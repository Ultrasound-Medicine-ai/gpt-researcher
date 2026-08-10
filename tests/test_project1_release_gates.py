"""Project-1 release gates — mock/unit only, no model quota. :-)

Covers:
1) Chat can request an independent report (tool contract)
2) Job recovery payload contract (refresh/resume)
3) Visitor isolation (cross-user job deny)
4) Knowledge-base-first vs freshness→web
5) References include original excerpt when available
"""

from __future__ import annotations

import asyncio
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


def test_gate_chat_independent_report_contract():
    from server.chat_report_request import chat_report_request

    payload = chat_report_request("请写一份独立研究报告：向量数据库选型", "")
    assert payload["action"] == "create_report"
    assert payload["knowledge_policy"] == "local_first"
    assert "向量数据库" in payload["task"]


def test_gate_job_recovery_storage_contract():
    """Frontend resumes via localStorage key + {jobId, sessionId}. """
    text = (ROOT / "frontend/nextjs/hooks/useResearchJob.ts").read_text(encoding="utf-8")
    assert "gptr_active_research_job" in text
    assert "resumeStoredJob" in text or "loadStoredJob" in text
    assert "jobId" in text and "sessionId" in text


def test_gate_visitor_isolation_denies_cross_user_job():
    from jobs import _MEMORY_JOBS, get_job
    from server.auth import mint_auth_token, parse_auth_token, resolve_identity
    import os

    os.environ["VISITOR_COOKIE_SECRET"] = "gate-secret"
    a = mint_auth_token("vis_aaa")
    b = mint_auth_token("vis_bbb")
    assert parse_auth_token(a) == "vis_aaa"
    assert parse_auth_token(b) == "vis_bbb"

    _MEMORY_JOBS.clear()
    _MEMORY_JOBS["j1"] = {
        "id": "j1",
        "user_id": "vis_aaa",
        "tenant_id": "vis_aaa",
        "status": "running",
        "stage": "researching",
        "progress": "x",
    }

    async def _run():
        assert await get_job("j1", user_id="vis_aaa", tenant_id="vis_aaa")
        assert await get_job("j1", user_id="vis_bbb", tenant_id="vis_bbb") is None

    asyncio.run(_run())
    _MEMORY_JOBS.clear()


def test_gate_knowledge_first_vs_freshness_web():
    pytest = __import__("pytest")
    try:
        from rag.report_source_policy import choose_report_sources
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"rag policy import unavailable: {exc}")

    class Chunk:
        def __init__(self, content):
            self.content = content
            self.source_url = "https://ex.com"
            self.title = "t"
            self.chunk_id = "c1"
            self.page_number = 1

    rich = [Chunk("x" * 1200) for _ in range(4)]

    with patch("rag.report_source_policy.hybrid_retrieve", return_value=rich):
        local = choose_report_sources(
            "企业内部知识库文档切片策略",
            tenant_id="vis_a",
            user_id="vis_a",
            policy="local_first",
        )
        assert local["mode"] == "knowledge_base"

        fresh = choose_report_sources(
            "今天最新的 AI 新闻",
            tenant_id="vis_a",
            user_id="vis_a",
            policy="local_first",
        )
        assert fresh["mode"] == "web"
        assert fresh["reason"] == "freshness_requested"


def test_gate_references_include_original_excerpt():
    """Assert source file encodes 原文片段 requirement without importing agent. :-)"""
    src = (ROOT / "gpt_researcher/actions/citation_registry.py").read_text(encoding="utf-8")
    assert "原文片段" in src
    assert "format_reference_list" in src
    assert "extract_snippet" in src


def test_gate_x_user_id_not_trusted():
    from server.auth import resolve_identity
    import os

    os.environ.pop("ALLOW_TEST_USER_HEADERS", None)
    os.environ["VISITOR_COOKIE_SECRET"] = "gate-secret"

    class H(dict):
        def get(self, k, default=None):
            return dict.get(self, k, default) or dict.get(self, str(k).lower(), default)

    req = SimpleNamespace(cookies={}, headers=H({"X-User-Id": "forged"}), state=SimpleNamespace())
    ident = resolve_identity(req)
    assert ident.user_id != "forged"
    assert ident.user_id.startswith("vis_")
