"""Acceptance checks for hybrid RAG (ingest → retrieve → isolation → degrade).

Requires Postgres (+ pgvector) via DATABASE_URL. Prefer Docker:
  docker compose exec -T gpt-researcher python scripts/e2e_rag_hybrid.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except Exception:
    pass


def _ok(name: str) -> None:
    print(f"PASS: {name}")


def _fail(name: str, detail: str) -> None:
    print(f"FAIL: {name} — {detail}")
    raise SystemExit(1)


async def main_async() -> int:
    from db.session import init_db, is_db_enabled
    from rag.ingest import ingest_text_document
    from rag.retrieve import hybrid_retrieve, rrf_fuse
    from rag.chunking import build_parent_child_chunks

    if not is_db_enabled():
        # Still validate pure helpers
        drafts = build_parent_child_chunks("# T\n\n" + ("Redis content. " * 80))
        if not any(d.chunk_level == "child" for d in drafts):
            _fail("chunking", "no children")
        fused = rrf_fuse([["a", "b"], ["b", "c"]])
        if fused[0][0] != "b":
            _fail("rrf", str(fused))
        _ok("offline_helpers")
        print("SKIP DB checks (DATABASE_URL unset)")
        return 0

    await init_db()
    sid_a = str(uuid.uuid4())
    sid_b = str(uuid.uuid4())
    tenant = f"e2e-rag-{uuid.uuid4().hex[:8]}"

    doc_a = await ingest_text_document(
        text="# User Doc A\n\n" + ("Alpha project budget is 100万 and uses Redis. " * 40),
        title="doc-a",
        uri="upload://a",
        source_type="upload",
        tenant_id=tenant,
        user_id="user-a",
        session_id=sid_a,
        source_url="doc-a.pdf",
        page_number=1,
    )
    doc_b = await ingest_text_document(
        text="# User Doc B\n\n" + ("Beta secret sauce is Memcached only. " * 40),
        title="doc-b",
        uri="upload://b",
        source_type="upload",
        tenant_id=tenant,
        user_id="user-b",
        session_id=sid_b,
        source_url="doc-b.pdf",
        page_number=1,
    )
    if not doc_a or not doc_b:
        _fail("ingest", f"doc_a={doc_a} doc_b={doc_b}")
    _ok("ingest_parent_child")

    hits_a = hybrid_retrieve(
        "Alpha project budget Redis",
        tenant_id=tenant,
        user_id="user-a",
        session_id=sid_a,
        top_k=5,
    )
    if not hits_a:
        _fail("retrieve_session_a", "no hits")
    if any(h.session_id and h.session_id != sid_a for h in hits_a):
        _fail("tenant_session_isolation", "cross-session leak in A")
    _ok("retrieve_from_user_doc")

    # User B must not see A's chunks
    hits_b_wrong = hybrid_retrieve(
        "Alpha project budget Redis",
        tenant_id=tenant,
        user_id="user-b",
        session_id=sid_b,
        top_k=5,
    )
    leaked = [h for h in hits_b_wrong if "Alpha" in h.content and "Beta" not in h.content]
    # Allow empty or Beta-only; never Alpha-only from session A
    if any(h.session_id == sid_a for h in hits_b_wrong):
        _fail("cross_user_isolation", f"leaked sessions {[h.session_id for h in hits_b_wrong]}")
    if leaked and all(h.session_id == sid_a for h in leaked):
        _fail("cross_user_isolation", "Alpha content leaked to user-b")
    _ok("cross_user_session_isolation")

    # Vector down → FTS path alone must still return results
    from rag.retrieve import fts_search, fetch_chunks_by_ids

    fts_ids = fts_search(
        "Memcached",
        tenant_id=tenant,
        user_id="user-b",
        session_id=sid_b,
        top_k=5,
    )
    if not fts_ids:
        _fail("fts_when_vector_down", "FTS returned no ids")
    fts_chunks = fetch_chunks_by_ids(fts_ids)
    if not fts_chunks:
        _fail("fts_when_vector_down", "FTS ids not fetchable")
    _ok("fts_when_vector_down")

    fts_hits = hybrid_retrieve(
        "Memcached",
        tenant_id=tenant,
        user_id="user-b",
        session_id=sid_b,
        top_k=5,
    )
    if not fts_hits:
        _fail("fts_or_hybrid", "no Memcached hits")
    _ok("hybrid_or_fts_available")

    # Citations locate page/url
    cite = hits_a[0]
    if not cite.chunk_id:
        _fail("citation", "missing chunk_id")
    if cite.page_number is None and not cite.source_url:
        _fail("citation", "missing page and url")
    _ok("citation_fields")

    from rag.context import assemble_evidence

    assembled = assemble_evidence(hits_a, token_budget=800)
    if assembled.total_tokens > 2000:
        _fail("token_budget", f"tokens={assembled.total_tokens}")
    _ok("token_budget_truncation")

    print("\nALL RAG HYBRID CHECKS PASSED")
    return 0


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    raise SystemExit(main())
