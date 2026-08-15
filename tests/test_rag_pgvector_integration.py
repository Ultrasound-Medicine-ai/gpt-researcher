"""Opt-in real PostgreSQL/pgvector verification for the current RAG chain."""

from __future__ import annotations

import asyncio
import json
import os
import unittest
from collections import Counter
from unittest.mock import patch

from rag.chunking import _tail_within_tokens, child_overlap_tokens
from rag.context import assemble_evidence, build_full_context
from rag.ingest import ingest_text_document
from rag.retrieve import (
    _fetch_siblings,
    expand_neighbors_from_siblings,
    fetch_chunks_by_ids,
    fts_search,
    hybrid_retrieve,
    rrf_fuse,
    vector_search,
)


SOURCE_DOCUMENT_IDS = (
    "7e304448-b843-4b99-ac1a-d65734f25dd6",
    "846bff83-197d-4a60-8a90-f5071167a8a2",
    "a837e776-27f7-4811-8c0a-5138f92033f6",
)
TENANT_ID = "rag-eval-candidates-v1"
USER_ID = "retrieval-eval"


def _dsn() -> str:
    return (os.getenv("DATABASE_URL") or "").replace(
        "postgresql+asyncpg://", "postgresql://", 1
    ).replace("postgresql+psycopg://", "postgresql://", 1)


def _load_source_documents() -> list[dict]:
    import psycopg

    sql = """
        SELECT d.id::text, d.title, c.title, c.content
        FROM documents d
        JOIN document_chunks c ON c.document_id = d.id
        WHERE d.id = ANY(%s::uuid[]) AND c.chunk_level = 'parent'
        ORDER BY d.id, c.created_at, c.id
    """
    with psycopg.connect(_dsn()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, [list(SOURCE_DOCUMENT_IDS)])
            rows = cursor.fetchall()
    grouped: dict[str, dict] = {}
    for document_id, document_title, section_title, content in rows:
        item = grouped.setdefault(
            document_id,
            {"id": document_id, "title": document_title, "sections": []},
        )
        item["sections"].append((section_title or document_title, content or ""))
    return list(grouped.values())


async def _reingest_sources(sources: list[dict]) -> list[str]:
    from db.session import close_db, init_db

    await init_db()
    document_ids = []
    try:
        for source in sources:
            text = "\n\n".join(
                f"## {heading}\n\n{content}" for heading, content in source["sections"]
            )
            document_id = await ingest_text_document(
                text=text,
                title=f"Retrieval candidate: {source['title']}",
                uri=f"retrieval-eval://{source['id']}",
                source_type="retrieval_eval_candidate",
                tenant_id=TENANT_ID,
                user_id=USER_ID,
                metadata={"original_document_id": source["id"], "candidate": True},
                replace_same_checksum=False,
            )
            assert document_id
            document_ids.append(document_id)
        return document_ids
    finally:
        await close_db()


def _existing_candidate_documents(sources: list[dict]) -> list[str]:
    import psycopg

    uris = [f"retrieval-eval://{source['id']}" for source in sources]
    sql = """
        SELECT DISTINCT ON (uri) uri, id::text
        FROM documents
        WHERE tenant_id = %s AND user_id = %s
          AND source_type = 'retrieval_eval_candidate'
          AND uri = ANY(%s)
        ORDER BY uri, created_at DESC
    """
    with psycopg.connect(_dsn()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, [TENANT_ID, USER_ID, uris])
            by_uri = dict(cursor.fetchall())
    return [by_uri[uri] for uri in uris if uri in by_uri]


def _prepare_documents(sources: list[dict]) -> list[str]:
    existing = _existing_candidate_documents(sources)
    if len(existing) == len(sources) and os.getenv("RAG_FORCE_REINGEST") != "1":
        return existing
    return asyncio.run(_reingest_sources(sources))


def _stored_counts(document_ids: list[str]) -> tuple[int, int, bool]:
    import psycopg

    sql = """
        SELECT chunk_level, parent_id::text, metadata_json
        FROM document_chunks
        WHERE document_id = ANY(%s::uuid[])
        ORDER BY parent_id, created_at, id
    """
    with psycopg.connect(_dsn()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, [document_ids])
            rows = cursor.fetchall()
    parents = sum(level == "parent" for level, _, _ in rows)
    children = [(parent_id, metadata or {}) for level, parent_id, metadata in rows if level == "child"]
    indexes: dict[str, list[int]] = {}
    for parent_id, metadata in children:
        indexes.setdefault(parent_id, []).append(int(metadata["child_index"]))
    stable = all(sorted(values) == list(range(len(values))) for values in indexes.values())
    return parents, len(children), stable


def _load_multi_child_family(document_ids: list[str]):
    import psycopg

    sql = """
        SELECT c.id::text
        FROM document_chunks c
        WHERE c.parent_id = (
            SELECT parent_id
            FROM document_chunks
            WHERE document_id = ANY(%s::uuid[]) AND chunk_level = 'child'
            GROUP BY parent_id
            HAVING count(*) > 1
            ORDER BY count(*) DESC
            LIMIT 1
        )
        AND c.chunk_level = 'child'
        ORDER BY (c.metadata_json->>'child_index')::int
    """
    with psycopg.connect(_dsn()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, [document_ids])
            ids = [row[0] for row in cursor.fetchall()]
    chunks = fetch_chunks_by_ids(ids)
    return [chunks[chunk_id] for chunk_id in ids]


@unittest.skipUnless(
    os.getenv("RUN_RAG_PGVECTOR_INTEGRATION") == "1",
    "set RUN_RAG_PGVECTOR_INTEGRATION=1 for the real database test",
)
class RealPgvectorIntegrationTest(unittest.TestCase):
    def test_real_parent_child_pgvector_chain(self):
        sources = _load_source_documents()
        self.assertEqual(len(sources), 3)
        document_ids = _prepare_documents(sources)
        parent_count, child_count, indexes_stable = _stored_counts(document_ids)
        self.assertGreater(parent_count, 0)
        self.assertGreaterEqual(child_count, parent_count)
        self.assertTrue(indexes_stable)

        fts_ids = fts_search(
            "Redis", tenant_id=TENANT_ID, user_id=USER_ID, top_k=20
        )
        vector_ids = vector_search(
            "Which in-memory data system supports persistence and failover?",
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            top_k=20,
        )
        self.assertTrue(fts_ids)
        self.assertTrue(vector_ids)
        self.assertTrue(rrf_fuse([fts_ids, vector_ids]))

        with patch("rag.retrieve.fts_search", return_value=fts_ids), patch(
            "rag.retrieve.vector_search", return_value=vector_ids
        ):
            hybrid = hybrid_retrieve(
                "Redis persistence and failover",
                tenant_id=TENANT_ID,
                user_id=USER_ID,
                top_k=8,
            )
        self.assertTrue(hybrid)
        core_counts = Counter(
            chunk.parent_id for chunk in hybrid if chunk.retrieval_priority in (0, 2)
        )
        self.assertTrue(all(count <= 2 for count in core_counts.values()))

        family = _load_multi_child_family(document_ids)
        self.assertGreater(len(family), 1)
        core_hit = family[min(1, len(family) - 1)]
        core_hit.retrieval_rank = 0
        siblings = _fetch_siblings(
            [core_hit], tenant_id=TENANT_ID, user_id=USER_ID, session_id=None
        )
        neighbors = expand_neighbors_from_siblings(
            [core_hit], siblings, radius=1, excluded_ids={core_hit.chunk_id}
        )
        self.assertTrue(neighbors)
        self.assertTrue(
            all(
                abs(int(chunk.child_index) - int(core_hit.child_index)) == 1
                for chunk in neighbors
            )
        )

        adjacent = None
        by_parent: dict[str, list] = {}
        for chunk in siblings:
            by_parent.setdefault(chunk.parent_id, []).append(chunk)
        for family in by_parent.values():
            family.sort(key=lambda chunk: int(chunk.child_index))
            if len(family) > 1:
                adjacent = family[:2]
                break
        if adjacent:
            overlap = _tail_within_tokens(adjacent[0].content, child_overlap_tokens())
            self.assertTrue(overlap and adjacent[1].content.startswith(overlap))
            assembled_pair = assemble_evidence(adjacent, token_budget=3500)
            self.assertIn(
                f"child_ids={adjacent[0].chunk_id},{adjacent[1].chunk_id}",
                assembled_pair.evidence_block,
            )
            self.assertEqual(
                [citation.chunk_id for citation in assembled_pair.citations],
                [adjacent[0].chunk_id, adjacent[1].chunk_id],
            )
            self.assertEqual(assembled_pair.evidence_block.count(overlap), 1)

        context = build_full_context(messages=[], children=hybrid)
        self.assertLessEqual(context.total_tokens, 3500)

        with patch("rag.retrieve.vector_search", return_value=[]):
            fts_only = hybrid_retrieve(
                "Redis", tenant_id=TENANT_ID, user_id=USER_ID, top_k=8
            )
        self.assertTrue(fts_only)

        result = {
            "documents": len(document_ids),
            "parents": parent_count,
            "children": child_count,
            "child_index_stable": indexes_stable,
            "fts_children": len(fts_ids),
            "vector_children": len(vector_ids),
            "hybrid_children": len(hybrid),
            "neighbor_children": len(neighbors),
            "context_token_count_estimated": context.total_tokens,
            "document_ids": document_ids,
        }
        print("RAG_INTEGRATION_RESULT=" + json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
