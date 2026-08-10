"""Build a lightweight document map from Parent chunks (no per-chunk LLM)."""

from __future__ import annotations

import logging
from typing import Any, Optional

from trusted_report.models import DocumentMapEntry, MapSection

logger = logging.getLogger(__name__)

_EXCERPT_CHARS = 280


def truncate_excerpt(text: str, limit: int = _EXCERPT_CHARS) -> str:
    text = (text or "").strip().replace("\n", " ")
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def build_document_map_from_rows(
    rows: list[dict[str, Any]],
    *,
    child_counts: Optional[dict[str, int]] = None,
) -> list[DocumentMapEntry]:
    """
    Pure helper: assemble DocumentMapEntry list from parent chunk rows.

    Each row keys: document_id, parent_chunk_id, title, heading/content,
    source_type, source_url, page_number, position (optional).
    Never calls an LLM.
    """
    child_counts = child_counts or {}
    by_doc: dict[str, DocumentMapEntry] = {}
    for i, row in enumerate(rows):
        doc_id = str(row.get("document_id") or "")
        if not doc_id:
            continue
        entry = by_doc.get(doc_id)
        if entry is None:
            entry = DocumentMapEntry(
                document_id=doc_id,
                title=str(row.get("doc_title") or row.get("title") or ""),
                source_type=str(row.get("source_type") or "web"),
                published_at=str(row.get("published_at") or ""),
                source_quality=str(row.get("source_quality") or ""),
            )
            by_doc[doc_id] = entry
        parent_id = str(row.get("parent_chunk_id") or row.get("id") or "")
        heading = str(row.get("heading") or row.get("title") or f"Section {i + 1}")
        excerpt = truncate_excerpt(str(row.get("summary_or_excerpt") or row.get("content") or ""))
        entry.sections.append(
            MapSection(
                parent_chunk_id=parent_id,
                heading=heading,
                position=int(row.get("position") or len(entry.sections) + 1),
                summary_or_excerpt=excerpt,
                child_count=int(child_counts.get(parent_id, row.get("child_count") or 0)),
            )
        )
    return list(by_doc.values())


def document_map_for_planner(
    entries: list[DocumentMapEntry],
    *,
    max_docs: int = 12,
    max_sections_per_doc: int = 8,
) -> list[dict[str, Any]]:
    """Trim map for Planner context — parents/excerpts only, never full children."""
    out: list[dict[str, Any]] = []
    for entry in entries[:max_docs]:
        d = entry.to_dict()
        d["sections"] = d["sections"][:max_sections_per_doc]
        out.append(d)
    return out


def build_document_map(
    *,
    tenant_id: str,
    session_id: Optional[str] = None,
    research_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> list[DocumentMapEntry]:
    """Load parent chunks from Postgres under tenant/session scope."""
    conn = _dsn()
    if not conn:
        return []
    sid = session_id or research_id
    clauses = ["c.chunk_level = 'parent'", "c.tenant_id = %s"]
    params: list[Any] = [tenant_id]
    if user_id and user_id != "anonymous":
        clauses.append("c.user_id = %s")
        params.append(user_id)
    if sid:
        clauses.append("c.session_id = %s")
        params.append(str(sid))
    where = " AND ".join(clauses)
    sql = f"""
        SELECT c.id::text AS parent_chunk_id,
               c.document_id::text AS document_id,
               c.title AS heading,
               c.content,
               c.source_url,
               d.title AS doc_title,
               coalesce(d.source_type, '') AS source_type,
               coalesce(d.metadata_json->>'published_at', '') AS published_at,
               coalesce(d.metadata_json->>'source_quality', '') AS source_quality,
               (
                 SELECT count(*) FROM document_chunks ch
                 WHERE ch.parent_id = c.id AND ch.chunk_level = 'child'
               ) AS child_count
        FROM document_chunks c
        LEFT JOIN documents d ON d.id = c.document_id
        WHERE {where}
        ORDER BY c.created_at ASC
        LIMIT 200
    """
    try:
        import psycopg

        with psycopg.connect(conn) as connection:
            with connection.cursor() as cur:
                cur.execute(sql, params)
                cols = [d.name for d in cur.description]
                rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        return build_document_map_from_rows(rows)
    except Exception as exc:
        logger.warning("build_document_map failed: %s", exc)
        return []


def _dsn() -> str:
    import os

    conn = (
        os.getenv("PGVECTOR_CONNECTION_STRING")
        or os.getenv("DATABASE_URL")
        or ""
    ).strip()
    if conn.startswith("postgresql+asyncpg://"):
        conn = conn.replace("postgresql+asyncpg://", "postgresql://", 1)
    elif conn.startswith("postgresql+psycopg://"):
        conn = conn.replace("postgresql+psycopg://", "postgresql://", 1)
    return conn
