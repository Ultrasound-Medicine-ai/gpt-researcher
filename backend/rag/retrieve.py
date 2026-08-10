"""Hybrid retrieval: PG FTS + vector cosine, fused with RRF."""

from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    parent_id: Optional[str]
    content: str
    title: str
    page_number: Optional[int]
    source_url: str
    token_estimate: int
    score: float
    source_type: str = ""
    tenant_id: str = ""
    session_id: Optional[str] = None


def _env_int(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    try:
        return max(1, int(raw)) if raw else default
    except ValueError:
        return default


def rrf_fuse(
    ranked_lists: list[list[str]],
    *,
    k: int = 60,
) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion over lists of chunk_id."""
    scores: dict[str, float] = {}
    for results in ranked_lists:
        for rank, cid in enumerate(results, start=1):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def _dsn() -> str:
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


def _scope_sql(
    *,
    tenant_id: str,
    user_id: Optional[str],
    session_id: Optional[str],
) -> tuple[str, list[Any]]:
    clauses = ["c.chunk_level = 'child'", "c.tenant_id = %s"]
    params: list[Any] = [tenant_id]
    # Strict tenant isolation; optional user + session narrowing
    if user_id and user_id != "anonymous":
        clauses.append("c.user_id = %s")
        params.append(user_id)
    if session_id:
        clauses.append("c.session_id = %s")
        params.append(str(session_id))
    return " AND ".join(clauses), params


def fts_search(
    query: str,
    *,
    tenant_id: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    top_k: int = 20,
) -> list[str]:
    """Return child chunk ids ordered by FTS rank."""
    conn = _dsn()
    if not conn or not query.strip():
        return []
    where, params = _scope_sql(
        tenant_id=tenant_id, user_id=user_id, session_id=session_id
    )
    sql = f"""
        SELECT c.id::text
        FROM document_chunks c
        WHERE {where}
          AND c.content_tsv @@ plainto_tsquery('simple', %s)
        ORDER BY ts_rank_cd(c.content_tsv, plainto_tsquery('simple', %s)) DESC
        LIMIT %s
    """
    params.extend([query, query, top_k])
    try:
        import psycopg

        with psycopg.connect(conn) as connection:
            with connection.cursor() as cur:
                cur.execute(sql, params)
                return [row[0] for row in cur.fetchall()]
    except Exception as exc:
        logger.warning("FTS search failed: %s", exc)
        return []


def vector_search(
    query: str,
    *,
    tenant_id: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    top_k: int = 20,
) -> list[str]:
    """Return child chunk ids by cosine distance. Empty if embedding unavailable."""
    conn = _dsn()
    if not conn or not query.strip():
        return []
    try:
        from gpt_researcher.config.config import Config
        from gpt_researcher.memory.embeddings import create_memory_with_failover

        cfg = Config()
        emb = create_memory_with_failover(
            cfg.embedding_provider,
            cfg.embedding_model,
            **cfg.embedding_kwargs,
        ).get_embeddings()
        vector = list(emb.embed_query(query))
    except Exception as exc:
        logger.warning("Vector query embed failed — FTS-only: %s", exc)
        try:
            from gpt_researcher.utils.dep_resilience import record_degradation

            record_degradation("rag", f"vector_query:{exc}"[:280], rag_degraded=True)
        except Exception:
            pass
        return []

    where, params = _scope_sql(
        tenant_id=tenant_id, user_id=user_id, session_id=session_id
    )
    # pgvector expects literal or adapted vector
    vec_literal = "[" + ",".join(str(float(x)) for x in vector) + "]"
    sql = f"""
        SELECT c.id::text
        FROM document_chunks c
        WHERE {where}
          AND c.embedding IS NOT NULL
        ORDER BY c.embedding <=> %s::vector
        LIMIT %s
    """
    params.extend([vec_literal, top_k])
    try:
        import psycopg

        with psycopg.connect(conn) as connection:
            with connection.cursor() as cur:
                cur.execute(sql, params)
                return [row[0] for row in cur.fetchall()]
    except Exception as exc:
        logger.warning("Vector search failed: %s", exc)
        try:
            from gpt_researcher.utils.dep_resilience import record_degradation

            record_degradation("rag", f"vector_search:{exc}"[:280], rag_degraded=True)
        except Exception:
            pass
        return []


def fetch_chunks_by_ids(chunk_ids: list[str]) -> dict[str, RetrievedChunk]:
    if not chunk_ids:
        return {}
    conn = _dsn()
    if not conn:
        return {}
    try:
        import psycopg

        sql = """
            SELECT c.id::text, c.document_id::text, c.parent_id::text,
                   c.content, c.title, c.page_number, c.source_url,
                   c.token_estimate, c.tenant_id, c.session_id::text,
                   coalesce(d.source_type, '')
            FROM document_chunks c
            LEFT JOIN documents d ON d.id = c.document_id
            WHERE c.id = ANY(%s::uuid[])
        """
        with psycopg.connect(conn) as connection:
            with connection.cursor() as cur:
                cur.execute(sql, [chunk_ids])
                rows = cur.fetchall()
        out: dict[str, RetrievedChunk] = {}
        for row in rows:
            out[row[0]] = RetrievedChunk(
                chunk_id=row[0],
                document_id=row[1],
                parent_id=row[2],
                content=row[3] or "",
                title=row[4] or "",
                page_number=row[5],
                source_url=row[6] or "",
                token_estimate=int(row[7] or 0),
                score=0.0,
                tenant_id=row[8] or "",
                session_id=row[9],
                source_type=row[10] or "",
            )
        return out
    except Exception as exc:
        logger.warning("fetch_chunks_by_ids failed: %s", exc)
        return {}


def hybrid_retrieve(
    query: str,
    *,
    tenant_id: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    top_k: Optional[int] = None,
) -> list[RetrievedChunk]:
    """Parallel-ish FTS + vector → RRF → Top-K child chunks."""
    top_k = top_k or _env_int("RAG_TOP_K", 8)
    pool = max(top_k * 3, 20)
    fts_ids = fts_search(
        query,
        tenant_id=tenant_id,
        user_id=user_id,
        session_id=session_id,
        top_k=pool,
    )
    vec_ids = vector_search(
        query,
        tenant_id=tenant_id,
        user_id=user_id,
        session_id=session_id,
        top_k=pool,
    )
    lists = [lst for lst in (fts_ids, vec_ids) if lst]
    if not lists:
        # Last-resort ILIKE keyword within scope
        lists = [
            _ilike_fallback(
                query,
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=session_id,
                top_k=pool,
            )
        ]
    fused = rrf_fuse(lists)
    # Optional rerank (fails open to RRF)
    try:
        from rag.rerank import maybe_rerank_ids

        fused_ids = maybe_rerank_ids(query, [cid for cid, _ in fused], top_k=top_k)
        ordered = fused_ids
        score_map = {cid: score for cid, score in fused}
    except Exception:
        ordered = [cid for cid, _ in fused[:top_k]]
        score_map = {cid: score for cid, score in fused}

    by_id = fetch_chunks_by_ids(ordered)
    results: list[RetrievedChunk] = []
    for cid in ordered:
        chunk = by_id.get(cid)
        if not chunk:
            continue
        # Enforce tenant filter in-process (defense in depth)
        if chunk.tenant_id and chunk.tenant_id != tenant_id:
            continue
        if session_id and chunk.session_id and chunk.session_id != str(session_id):
            continue
        chunk.score = float(score_map.get(cid, 0.0))
        results.append(chunk)
        if len(results) >= top_k:
            break
    return results


def _ilike_fallback(
    query: str,
    *,
    tenant_id: str,
    user_id: Optional[str],
    session_id: Optional[str],
    top_k: int,
) -> list[str]:
    from gpt_researcher.utils.dep_resilience import tokenize_query

    tokens = tokenize_query(query)[:6]
    if not tokens:
        return []
    conn = _dsn()
    if not conn:
        return []
    where, params = _scope_sql(
        tenant_id=tenant_id, user_id=user_id, session_id=session_id
    )
    likes = " OR ".join(["c.content ILIKE %s"] * len(tokens))
    params.extend([f"%{t}%" for t in tokens])
    params.append(top_k)
    sql = f"""
        SELECT c.id::text FROM document_chunks c
        WHERE {where} AND ({likes})
        LIMIT %s
    """
    try:
        import psycopg

        with psycopg.connect(conn) as connection:
            with connection.cursor() as cur:
                cur.execute(sql, params)
                return [r[0] for r in cur.fetchall()]
    except Exception as exc:
        logger.debug("ILIKE fallback failed: %s", exc)
        return []
