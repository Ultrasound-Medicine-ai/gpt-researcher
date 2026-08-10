"""Unit tests for search/scrape/embedding degradation helpers."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "backend"):
    p = str(path)
    if p not in sys.path:
        sys.path.insert(0, p)


def _load(name: str, rel: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(autouse=True)
def _reset_circuits():
    dep = _load("dep_resilience_under_test", "gpt_researcher/utils/dep_resilience.py")
    dep.reset_circuits_for_tests()
    yield
    dep.reset_circuits_for_tests()


def test_circuit_opens_after_threshold():
    dep = sys.modules["dep_resilience_under_test"]
    cb = dep.CircuitBreaker("t", failure_threshold=2, cooldown_sec=60)
    assert cb.allow()
    cb.record_failure("a")
    assert cb.allow()
    cb.record_failure("b")
    assert not cb.allow()
    assert cb.snapshot()["open"] is True


def test_keyword_select_documents_ranks_hits():
    dep = sys.modules["dep_resilience_under_test"]
    docs = [
        {"url": "a", "raw_content": "unrelated gardening tips"},
        {"url": "b", "raw_content": "Redis cache latency and Redis clustering"},
        {"url": "c", "raw_content": "Memcached vs Redis comparison guide"},
    ]
    selected = dep.keyword_select_documents("Redis vs Memcached", docs, max_results=2)
    urls = [d["url"] for d in selected]
    assert "a" not in urls or urls[0] != "a"
    assert any(u in ("b", "c") for u in urls)


def test_should_rotate_on_timeout_and_429():
    key_pool = _load(
        "tavily_key_pool_under_test",
        "gpt_researcher/retrievers/tavily/key_pool.py",
    )
    assert key_pool.should_rotate_tavily_key(status_code=429, error_message="rate limit")
    assert key_pool.should_rotate_tavily_key(error_message="request timed out")
    assert key_pool.should_rotate_tavily_key(exception=TimeoutError("timeout"))


@pytest.mark.asyncio
async def test_runtime_records_rag_degraded():
    from jobs.runtime import JobRuntime

    rt = JobRuntime("j1", "w1", 1)
    rt.record_degradation("rag", "keyword_fallback", rag_degraded=True)
    rt.record_degradation("scrape", "timeout", url="https://x.test", quality="failed")
    cost = rt.cost_trace()
    assert cost["rag_degraded"] is True
    assert cost["scrape_failures"] >= 1


def test_embedding_candidates_default_and_env(monkeypatch):
    # Load embeddings helpers without package import (avoid match on py3.9)
    src = (ROOT / "gpt_researcher" / "memory" / "embeddings.py").read_text(
        encoding="utf-8"
    )
    assert "EMBEDDING_FALLBACKS" in src
    assert "_embedding_candidates" in src
    assert "create_memory_with_failover" in src
    assert "_filter_candidates_by_dim" in src
    assert "_STICKY_EMBEDDING" in src
    # LangChain retrievers validate the object against this base class.  A
    # duck-typed wrapper is rejected before embed_query can execute.
    assert "class _FailoverEmbeddings(Embeddings)" in src
    monkeypatch.setenv("EMBEDDING_DIM", "1536")
    monkeypatch.setenv(
        "EMBEDDING_FALLBACKS",
        "dashscope:text-embedding-v1,ollama:nomic-embed-text",
    )
    ns: dict = {"os": __import__("os")}
    exec(
        """
_KNOWN_EMBEDDING_DIMS = {
    ("dashscope", "text-embedding-v1"): 1536,
    ("dashscope", "text-embedding-v2"): 1536,
    ("ollama", "nomic-embed-text"): 768,
}

def expected_embedding_dim():
    raw = (os.environ.get("EMBEDDING_DIM") or "1536").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 1536

def _known_dim(provider, model):
    return _KNOWN_EMBEDDING_DIMS.get((provider.lower(), model.strip()))

def _filter_candidates_by_dim(candidates):
    target = expected_embedding_dim()
    kept = []
    for p, m in candidates:
        dim = _known_dim(p, m)
        if dim is not None and dim != target:
            continue
        kept.append((p, m))
    return kept

def _embedding_candidates(provider, model):
    candidates = [(provider, model)]
    raw = os.environ.get("EMBEDDING_FALLBACKS", "").strip()
    if not raw and provider == "dashscope" and model == "text-embedding-v2":
        raw = "dashscope:text-embedding-v1"
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry or ":" not in entry:
            continue
        p, m = entry.split(":", 1)
        cand = (p.strip(), m.strip())
        if cand not in candidates:
            candidates.append(cand)
    return _filter_candidates_by_dim(candidates)
""",
        ns,
    )
    cands = ns["_embedding_candidates"]("dashscope", "text-embedding-v2")
    assert ("dashscope", "text-embedding-v1") in cands
    assert ("ollama", "nomic-embed-text") not in cands
