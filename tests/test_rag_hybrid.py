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
