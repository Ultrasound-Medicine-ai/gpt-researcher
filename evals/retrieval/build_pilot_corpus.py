"""Build the reviewed-pilot corpus from existing persisted technical documents."""

from __future__ import annotations

import argparse
import asyncio
import json
import os

from rag.chunking import build_parent_child_chunks
from rag.ingest import ingest_text_document

TENANT_ID = "rag-retrieval-corpus-v1"
USER_ID = "retrieval-eval"
SOURCE_DOCUMENT_IDS = (
    "d26a56ee-d3ed-48e4-924a-b7dd23a1b8da",
    "9082badc-9375-4aa4-812a-dee00fa836e0",
    "c51bc96d-8bda-4382-829f-512d2f5c9bcc",
    "9e7f0623-b977-4fe4-b62b-79c6c2760ec8",
    "6cc72797-b054-4470-bd0b-9bb4c2a1a694",
    "dc171ecd-5397-4a27-b268-3f3d22aa8c68",
    "3be0ae7e-3e5c-44c3-824d-0383559aa4b0",
    "9ed83643-a766-4ea7-8dbd-d77b8c46f4d2",
    "f23721b2-65b2-47d9-bb2d-b5f762309eb6",
    "a8fffeae-c458-4e96-84c8-e5d92f59979f",
    "ff685ffd-1d26-41e0-8d43-7a149b0b636c",
    "d428b820-8862-4e6e-9193-ad6e03b12590",
    "d1b23ca7-0f97-4557-bc51-35ce10c8858b",
    "ad46dec4-fdc7-4d64-ac2b-3f8fcd6dd86b",
    "117dd150-e470-4a62-9a28-9a09eecc31d1",
    "0ae8894a-10cb-4327-af35-30b86c3d4384",
    "dffb2a73-9fe6-4ad1-819c-e7821a4986e8",
    "ce911289-07e6-4800-9fc5-08a14cfb067a",
    "44cf077e-1d5a-415f-87d6-99cb5f2efbb2",
    "23a5178f-cb8a-482b-a400-1fd17d323489",
    "62c2dccd-ea6d-4521-8015-b00feb3a9baa",
    "bd80535d-cc24-4435-a232-c2e634dc2d98",
    "6cc85b15-c314-40a5-8080-42f5f77070c1",
    "a82c31aa-e55c-4548-9414-ae02a1e42668",
    "5f04b1b6-1d8a-42dd-a605-7c2f77cc65be",
    "b7064d3c-cc6f-48f1-9b53-5faf8e7393c5",
    "8f845a6c-e7fd-40c5-b7ef-7feff0de60ab",
    "3bfc4f58-72f3-4390-af34-b7df8c9b75fb",
    "f55455a5-a1df-45ef-8de1-37c2e36ea7d5",
    "89075b92-926c-471e-90b9-35d0f342cc3d",
)


def _dsn() -> str:
    return (os.getenv("DATABASE_URL") or "").replace(
        "postgresql+asyncpg://", "postgresql://", 1
    ).replace("postgresql+psycopg://", "postgresql://", 1)


def load_sources() -> list[dict]:
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
    for document_id, document_title, heading, content in rows:
        item = grouped.setdefault(
            document_id,
            {"id": document_id, "title": document_title, "sections": []},
        )
        if (content or "").strip() != (heading or "").strip():
            item["sections"].append((heading or document_title, content or ""))
    return [grouped[document_id] for document_id in SOURCE_DOCUMENT_IDS if document_id in grouped]


def source_text(source: dict) -> str:
    return "\n\n".join(
        f"## {heading}\n\n{content}" for heading, content in source["sections"]
    )


def dry_run(sources: list[dict]) -> dict:
    parents = children = 0
    for source in sources:
        drafts = build_parent_child_chunks(source_text(source), title=source["title"])
        parents += sum(draft.chunk_level == "parent" for draft in drafts)
        children += sum(draft.chunk_level == "child" for draft in drafts)
    return {"documents": len(sources), "parents": parents, "children": children}


def existing_document_ids() -> list[str]:
    import psycopg

    uris = [f"retrieval-corpus://{source_id}" for source_id in SOURCE_DOCUMENT_IDS]
    sql = """
        SELECT DISTINCT ON (uri) uri, id::text
        FROM documents
        WHERE tenant_id = %s AND user_id = %s
          AND source_type = 'retrieval_eval_corpus' AND uri = ANY(%s)
        ORDER BY uri, created_at DESC
    """
    with psycopg.connect(_dsn()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, [TENANT_ID, USER_ID, uris])
            by_uri = dict(cursor.fetchall())
    return [by_uri[uri] for uri in uris if uri in by_uri]


async def ingest_sources(sources: list[dict]) -> list[str]:
    from db.session import close_db, init_db

    await init_db()
    document_ids = []
    try:
        for source in sources:
            document_id = await ingest_text_document(
                text=source_text(source),
                title=source["title"],
                uri=f"retrieval-corpus://{source['id']}",
                source_type="retrieval_eval_corpus",
                tenant_id=TENANT_ID,
                user_id=USER_ID,
                metadata={"original_document_id": source["id"], "pilot_corpus": True},
                replace_same_checksum=False,
            )
            if not document_id:
                raise RuntimeError(f"ingest failed: {source['id']}")
            document_ids.append(document_id)
        return document_ids
    finally:
        await close_db()


def corpus_stats(document_ids: list[str]) -> dict:
    import psycopg

    sql = """
        SELECT
          count(DISTINCT document_id) FILTER (WHERE chunk_level='child'),
          count(DISTINCT parent_id) FILTER (WHERE chunk_level='child'),
          count(*) FILTER (WHERE chunk_level='child'),
          avg(token_estimate) FILTER (WHERE chunk_level='child'),
          min(token_estimate) FILTER (WHERE chunk_level='child'),
          percentile_cont(0.25) WITHIN GROUP (ORDER BY token_estimate)
            FILTER (WHERE chunk_level='child'),
          percentile_cont(0.5) WITHIN GROUP (ORDER BY token_estimate)
            FILTER (WHERE chunk_level='child'),
          percentile_cont(0.75) WITHIN GROUP (ORDER BY token_estimate)
            FILTER (WHERE chunk_level='child'),
          percentile_cont(0.9) WITHIN GROUP (ORDER BY token_estimate)
            FILTER (WHERE chunk_level='child'),
          max(token_estimate) FILTER (WHERE chunk_level='child')
        FROM document_chunks WHERE document_id = ANY(%s::uuid[])
    """
    with psycopg.connect(_dsn()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, [document_ids])
            row = cursor.fetchone()
    documents, parents, children, avg_tok, min_tok, p25, p50, p75, p90, max_tok = row
    return {
        "document_count": documents,
        "parent_count": parents,
        "child_count": children,
        "average_children_per_parent": round(children / parents, 3),
        "child_token_distribution": {
            "min": min_tok,
            "p25": float(p25),
            "p50": float(p50),
            "p75": float(p75),
            "p90": float(p90),
            "max": max_tok,
            "mean": round(float(avg_tok), 3),
        },
        "document_ids": document_ids,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ingest", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    sources = load_sources()
    if len(sources) != len(SOURCE_DOCUMENT_IDS):
        raise RuntimeError(f"only {len(sources)}/{len(SOURCE_DOCUMENT_IDS)} sources found")
    estimate = dry_run(sources)
    print("CORPUS_DRY_RUN=" + json.dumps(estimate))
    if not args.ingest:
        return
    document_ids = [] if args.force else existing_document_ids()
    if len(document_ids) != len(sources):
        document_ids = asyncio.run(ingest_sources(sources))
    print("CORPUS_STATS=" + json.dumps(corpus_stats(document_ids), ensure_ascii=False))


if __name__ == "__main__":
    main()
