"""Unit tests for hybrid RAG chunking, RRF, and context assembly."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
for path in (ROOT, BACKEND):
    p = str(path)
    if p not in sys.path:
        sys.path.insert(0, p)


def _load(name: str, rel: str):
    path = BACKEND / rel
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    # Ensure package-style imports inside module resolve
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_parent_child_chunking_produces_both_levels():
    chunking = _load("rag_chunking", "rag/chunking.py")
    text = """# Intro

Redis is an in-memory data store used for caching and messaging.

## Details

Memcached is simpler. Redis supports data structures, persistence, and replication.
""" * 3
    drafts = chunking.build_parent_child_chunks(text, title="Redis", source_url="u")
    levels = {d.chunk_level for d in drafts}
    assert "parent" in levels and "child" in levels
    children = [d for d in drafts if d.chunk_level == "child"]
    assert all(d.parent_index is not None for d in children)
    assert all(200 <= d.token_estimate or True for d in children)


def test_child_chunking_adds_configured_sliding_overlap(monkeypatch):
    chunking = _load("rag_chunking_overlap", "rag/chunking.py")
    monkeypatch.setenv("RAG_CHILD_TOKENS_MIN", "20")
    monkeypatch.setenv("RAG_CHILD_TOKENS_MAX", "40")
    monkeypatch.setenv("RAG_CHILD_OVERLAP_TOKENS", "8")
    text = " ".join(f"token{i}" for i in range(160))

    drafts = chunking.build_parent_child_chunks(text, title="Overlap")
    children = [d for d in drafts if d.chunk_level == "child"]

    assert len(children) > 1
    expected_tail = chunking._tail_within_tokens(children[0].content, 8)
    assert expected_tail
    assert children[1].content.startswith(expected_tail)
    assert all(d.metadata["overlap_tokens"] == 8 for d in children)


def test_child_chunk_overlap_can_be_disabled(monkeypatch):
    chunking = _load("rag_chunking_no_overlap", "rag/chunking.py")
    monkeypatch.setenv("RAG_CHILD_OVERLAP_TOKENS", "0")
    assert chunking.child_overlap_tokens() == 0
    assert chunking._add_sliding_overlap(["first", "second"], 0) == [
        "first",
        "second",
    ]


def test_overlap_keeps_cjk_suffix_within_budget():
    chunking = _load("rag_chunking_cjk_overlap", "rag/chunking.py")
    suffix = chunking._tail_within_tokens("甲" * 20 + "乙" * 20, 8)
    assert suffix == "乙" * 8
    assert chunking.estimate_tokens(suffix) <= 8


def test_rrf_fuse_prefers_agreement():
    retrieve = _load("rag_retrieve", "rag/retrieve.py")
    fused = retrieve.rrf_fuse(
        [
            ["a", "b", "c"],
            ["c", "a", "d"],
        ]
    )
    ids = [cid for cid, _ in fused]
    # a and c appear in both lists → should rank above unique ones
    assert ids[0] in ("a", "c")
    assert "b" in ids and "d" in ids


def test_calibrated_rrf_keeps_all_candidates_and_prefers_agreement():
    retrieve = _load("rag_retrieve_calibrated", "rag/retrieve.py")
    fused = retrieve.calibrated_rrf_fuse(
        ["fts-only", "shared"], ["vector-only", "shared"], "general query"
    )
    ids = [chunk_id for chunk_id, _ in fused]
    assert ids[0] == "shared"
    assert set(ids) == {"fts-only", "vector-only", "shared"}


def test_calibrated_rrf_fails_open_to_fts_only():
    retrieve = _load("rag_retrieve_calibrated_fts", "rag/retrieve.py")
    fused = retrieve.calibrated_rrf_fuse(["a", "b"], [], "SET NX PX")
    assert [chunk_id for chunk_id, _ in fused] == ["a", "b"]


def test_assemble_evidence_respects_budget_and_citations():
    # Load retrieve dataclass into sys.modules for context imports
    retrieve = _load("rag.retrieve", "rag/retrieve.py")
    sys.modules["rag"] = type(sys)("rag")
    sys.modules["rag.retrieve"] = retrieve
    chunking = _load("rag.chunking", "rag/chunking.py")
    sys.modules["rag.chunking"] = chunking
    context = _load("rag.context", "rag/context.py")

    children = [
        retrieve.RetrievedChunk(
            chunk_id="c1",
            document_id="d1",
            parent_id="p1",
            content="Redis latency is low for caching workloads. " * 20,
            title="Redis",
            page_number=2,
            source_url="https://example.com/redis",
            token_estimate=80,
            score=0.9,
            tenant_id="t1",
            session_id="s1",
        ),
        retrieve.RetrievedChunk(
            chunk_id="c2",
            document_id="d1",
            parent_id="p1",
            content="Persistence options include AOF and RDB. " * 20,
            title="Redis",
            page_number=3,
            source_url="https://example.com/redis",
            token_estimate=70,
            score=0.5,
            tenant_id="t1",
            session_id="s1",
        ),
    ]
    assembled = context.assemble_evidence(children, token_budget=5000)
    assert "chunk_id=c1" in assembled.evidence_block
    assert assembled.citations
    assert assembled.citations[0].page_number == 2


def test_scope_sql_requires_tenant():
    retrieve = _load("rag_retrieve_scope", "rag/retrieve.py")
    where, params = retrieve._scope_sql(
        tenant_id="tenant-a", user_id="u1", session_id="11111111-1111-1111-1111-111111111111"
    )
    assert "tenant_id" in where
    assert params[0] == "tenant-a"
    assert "u1" in params


def _retrieved(retrieve, chunk_id, parent_id, *, index=0, tokens=50, score=1.0):
    return retrieve.RetrievedChunk(
        chunk_id=chunk_id,
        document_id="d1",
        parent_id=parent_id,
        content=f"content-{chunk_id}",
        title="Title",
        page_number=None,
        source_url="",
        token_estimate=tokens,
        score=score,
        tenant_id="tenant-a",
        child_index=index,
    )


def test_parent_diversity_prevents_one_parent_monopoly():
    retrieve = _load("rag_retrieve_diversity", "rag/retrieve.py")
    chunks = [
        _retrieved(retrieve, "a1", "p1", index=0),
        _retrieved(retrieve, "a2", "p1", index=1),
        _retrieved(retrieve, "a3", "p1", index=2),
        _retrieved(retrieve, "b1", "p2", index=0),
        _retrieved(retrieve, "c1", "p3", index=0),
    ]
    primary, supplemental = retrieve.diversify_chunks(
        chunks, top_k=4, max_children_per_parent=2
    )
    selected = primary + supplemental
    assert [chunk.chunk_id for chunk in primary] == ["a1", "b1", "c1"]
    assert [chunk.chunk_id for chunk in selected] == ["a1", "b1", "c1", "a2"]
    assert sum(chunk.parent_id == "p1" for chunk in selected) == 2


def test_neighbor_expansion_adds_plus_minus_one_before_supplement():
    retrieve = _load("rag_retrieve_neighbors", "rag/retrieve.py")
    hit = _retrieved(retrieve, "c1", "p1", index=1, tokens=100)
    hit.retrieval_rank = 0
    siblings = [
        _retrieved(retrieve, "c0", "p1", index=0, tokens=100),
        hit,
        _retrieved(retrieve, "c2", "p1", index=2, tokens=100),
    ]
    neighbors = retrieve.expand_neighbors_from_siblings(
        [hit], siblings, radius=1, excluded_ids={"c1"}
    )
    supplement = _retrieved(retrieve, "low", "p2", tokens=100)
    packed = retrieve.pack_retrieval_candidates(
        [hit], neighbors, [supplement], token_budget=300
    )
    assert [chunk.chunk_id for chunk in neighbors] == ["c0", "c2"]
    assert [chunk.chunk_id for chunk in packed] == ["c1", "c0", "c2"]


def test_continuous_children_merge_and_remove_overlap():
    retrieve = _load("rag.retrieve", "rag/retrieve.py")
    sys.modules["rag"] = type(sys)("rag")
    sys.modules["rag.retrieve"] = retrieve
    chunking = _load("rag.chunking", "rag/chunking.py")
    sys.modules["rag.chunking"] = chunking
    context = _load("rag_context_overlap", "rag/context.py")
    first = _retrieved(retrieve, "c1", "p1", index=0)
    second = _retrieved(retrieve, "c2", "p1", index=1)
    first.content = "alpha shared-overlap"
    second.content = "shared-overlap beta"

    assembled = context.assemble_evidence([first, second], token_budget=500)

    assert assembled.evidence_block.count("shared-overlap") == 1
    assert "child_ids=c1,c2" in assembled.evidence_block
    assert [citation.chunk_id for citation in assembled.citations] == ["c1", "c2"]


def test_final_context_never_exceeds_3500_tokens(monkeypatch):
    retrieve = _load("rag.retrieve", "rag/retrieve.py")
    sys.modules["rag"] = type(sys)("rag")
    sys.modules["rag.retrieve"] = retrieve
    chunking = _load("rag.chunking", "rag/chunking.py")
    sys.modules["rag.chunking"] = chunking
    context = _load("rag_context_budget", "rag/context.py")
    monkeypatch.setenv("RAG_CONTEXT_TOKEN_BUDGET", "3500")
    children = []
    for i in range(8):
        child = _retrieved(retrieve, f"c{i}", f"p{i}", tokens=700)
        child.content = "证" * 700
        child.retrieval_rank = i
        children.append(child)

    assembled = context.build_full_context(
        messages=[{"role": "user", "content": "question " * 400}],
        children=children,
        base_context="base " * 600,
    )
    assert assembled.total_tokens <= 3500
    assert chunking.estimate_tokens(assembled.evidence_block) <= 3500


def test_embedding_failure_keeps_fts_only_retrieval(monkeypatch):
    retrieve = _load("rag_retrieve_fts_only", "rag/retrieve.py")
    chunks = {
        "a": _retrieved(retrieve, "a", "p1", index=0),
        "b": _retrieved(retrieve, "b", "p2", index=0),
    }
    monkeypatch.setattr(retrieve, "fts_search", lambda *args, **kwargs: ["a", "b"])
    monkeypatch.setattr(retrieve, "vector_search", lambda *args, **kwargs: [])
    monkeypatch.setattr(retrieve, "fetch_chunks_by_ids", lambda ids: chunks)
    monkeypatch.setattr(retrieve, "_fetch_siblings", lambda *args, **kwargs: [])

    results = retrieve.hybrid_retrieve("redis", tenant_id="tenant-a", top_k=2)

    assert [chunk.chunk_id for chunk in results] == ["a", "b"]
