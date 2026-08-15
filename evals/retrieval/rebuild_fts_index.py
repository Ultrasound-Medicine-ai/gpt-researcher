"""Rebuild only PostgreSQL lexical vectors; chunk text, IDs, and embeddings stay intact."""

from __future__ import annotations

import hashlib
import os

import psycopg

from rag.fts import fts_index_text

TENANT_ID = "rag-retrieval-corpus-v1"
USER_ID = "retrieval-eval"


def _dsn() -> str:
    return os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://").replace("postgresql+psycopg://", "postgresql://")


def _child_snapshot(cursor) -> tuple[int, str]:
    cursor.execute(
        "SELECT id::text FROM document_chunks WHERE tenant_id=%s AND user_id=%s AND chunk_level='child' ORDER BY id",
        [TENANT_ID, USER_ID],
    )
    ids = [row[0] for row in cursor.fetchall()]
    return len(ids), hashlib.sha256("\n".join(ids).encode()).hexdigest()


def main() -> None:
    with psycopg.connect(_dsn()) as connection:
        with connection.cursor() as cursor:
            before = _child_snapshot(cursor)
            cursor.execute("SELECT id::text, title, content FROM document_chunks ORDER BY id")
            rows = cursor.fetchall()
            cursor.executemany(
                "UPDATE document_chunks SET content_tsv=to_tsvector('simple', %s) WHERE id=%s::uuid",
                [(fts_index_text(title, content), chunk_id) for chunk_id, title, content in rows],
            )
            after = _child_snapshot(cursor)
            cursor.execute(
                "SELECT count(*) FROM document_chunks WHERE tenant_id=%s AND user_id=%s AND chunk_level='child' AND content_tsv IS NOT NULL",
                [TENANT_ID, USER_ID],
            )
            indexed = cursor.fetchone()[0]
        connection.commit()
    if before != after or indexed != before[0]:
        raise RuntimeError(f"lexical rebuild invariant failed: before={before}, after={after}, indexed={indexed}")
    print(f"child_count={before[0]} child_id_sha256={before[1]} indexed_children={indexed}")


if __name__ == "__main__":
    main()
