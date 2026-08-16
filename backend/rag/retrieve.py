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
    child_index: Optional[int] = None
    retrieval_priority: int = 0  # 0=primary hit, 1=neighbor, 2=supplemental hit
    retrieval_rank: int = 0


def _env_int(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    try:
        return max(1, int(raw)) if raw else default
    except ValueError:
        return default


def _env_nonnegative_int(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    try:
        return max(0, int(raw)) if raw else default
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


def calibrated_rrf_fuse(
    fts_ids: list[str],
    vector_ids: list[str],
    query: str,
    *,
    k: int = 60,
) -> list[tuple[str, float]]:
    """Calibrate unequal rank sources without dropping either source's candidates."""
    if not fts_ids or not vector_ids:
        return rrf_fuse([ids for ids in (fts_ids, vector_ids) if ids], k=k)
    try:
        from rag.fts import fts_anchor_terms

        anchor_strength = min(1.0, len(fts_anchor_terms(query)) / 2)
    except Exception:
        anchor_strength = 0.0
    agreement = len(set(fts_ids[:8]).intersection(vector_ids[:8])) / 8
    fts_weight = 0.50 + 0.25 * agreement + 0.25 * anchor_strength
    scores: dict[str, float] = {}
    for rank, chunk_id in enumerate(vector_ids, start=1):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
    for rank, chunk_id in enumerate(fts_ids, start=1):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + fts_weight / (k + rank)
    vector_rank = {chunk_id: rank for rank, chunk_id in enumerate(vector_ids)}
    fts_rank = {chunk_id: rank for rank, chunk_id in enumerate(fts_ids)}
    return sorted(
        scores.items(),
        key=lambda item: (
            -item[1],
            vector_rank.get(item[0], 10_000),
            fts_rank.get(item[0], 10_000),
        ),
    )


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


def _active_episode_sql() -> str:
    """Exclude archived/expired episodic memory from the normal RAG path."""
    return (
        "(d.source_type <> 'chat_episode' OR "
        "coalesce(d.metadata_json->>'episode_status', 'active') = 'active')"
    )


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
    try:
        from rag.fts import fts_anchor_terms, fts_or_query, fts_terms

        tsquery = fts_or_query(query)
        terms = fts_terms(query)
        anchors = fts_anchor_terms(query)
    except Exception as exc:
        logger.warning("FTS query preparation failed: %s", exc)
        return []
    if not tsquery:
        return []
    sql = f"""
        WITH query_data AS (
            SELECT to_tsquery('simple', %s) AS query,
                   %s::text[] AS terms,
                   %s::text[] AS anchors
        )
        SELECT c.id::text
        FROM document_chunks c
        JOIN documents d ON d.id = c.document_id
        CROSS JOIN query_data q
        CROSS JOIN LATERAL (
            SELECT count(*) FILTER (
                       WHERE c.content_tsv @@ plainto_tsquery('simple', term)
                   )::float / greatest(cardinality(q.terms), 1) AS coverage
            FROM unnest(q.terms) AS term
        ) coverage_score
        CROSS JOIN LATERAL (
            SELECT count(*) FILTER (
                       WHERE c.content_tsv @@ plainto_tsquery('simple', anchor)
                   ) AS anchor_hits
            FROM unnest(q.anchors) AS anchor
        ) anchor_score
        WHERE {where} AND {_active_episode_sql()}
          AND c.content_tsv @@ q.query
        ORDER BY anchor_score.anchor_hits DESC,
                 coverage_score.coverage DESC,
                 ts_rank_cd(c.content_tsv, q.query, 32) DESC,
                 c.id
        LIMIT %s
    """
    params = [tsquery, terms, anchors, *params, top_k]
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
        from gpt_researcher.memory.embeddings import (
            create_memory_with_failover,
            expected_embedding_dim,
        )

        cfg = Config()
        emb = create_memory_with_failover(
            cfg.embedding_provider,
            cfg.embedding_model,
            **cfg.embedding_kwargs,
        ).get_embeddings()
        vector = list(emb.embed_query(query))
        expected = expected_embedding_dim()
        if len(vector) != expected:
            logger.warning(
                "Query embedding dim=%s != EMBEDDING_DIM=%s — FTS-only",
                len(vector),
                expected,
            )
            return []
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
        JOIN documents d ON d.id = c.document_id
        WHERE {where} AND {_active_episode_sql()}
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


def _chunk_from_row(row: tuple) -> RetrievedChunk:
    metadata = row[11] if len(row) > 11 and isinstance(row[11], dict) else {}
    try:
        child_index = int(metadata.get("child_index"))
    except (TypeError, ValueError):
        child_index = None
    return RetrievedChunk(
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
        child_index=child_index,
    )


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
                   coalesce(d.source_type, ''), c.metadata_json
            FROM document_chunks c
            LEFT JOIN documents d ON d.id = c.document_id
            WHERE c.id = ANY(%s::uuid[])
        """
        with psycopg.connect(conn) as connection:
            with connection.cursor() as cur:
                cur.execute(sql, [chunk_ids])
                rows = cur.fetchall()
        return {row[0]: _chunk_from_row(row) for row in rows}
    except Exception as exc:
        logger.warning("fetch_chunks_by_ids failed: %s", exc)
        return {}


def diversify_chunks(
    chunks: list[RetrievedChunk],
    *,
    top_k: int,
    max_children_per_parent: int,
) -> tuple[list[RetrievedChunk], list[RetrievedChunk]]:
    """Take one child per parent first, then capped same-parent supplements."""
    primary: list[RetrievedChunk] = []
    supplemental: list[RetrievedChunk] = []
    counts: dict[str, int] = {}
    for rank, chunk in enumerate(chunks):
        key = chunk.parent_id or chunk.chunk_id
        count = counts.get(key, 0)
        if count == 0:
            chunk.retrieval_priority = 0
            primary.append(chunk)
            counts[key] = 1
        elif count < max_children_per_parent:
            chunk.retrieval_priority = 2
            supplemental.append(chunk)
            counts[key] = count + 1
        chunk.retrieval_rank = rank

    if len(primary) >= top_k:
        return primary[:top_k], []
    return primary, supplemental[: top_k - len(primary)]


def expand_neighbors_from_siblings(
    hits: list[RetrievedChunk],
    siblings: list[RetrievedChunk],
    *,
    radius: int,
    excluded_ids: Optional[set[str]] = None,
) -> list[RetrievedChunk]:
    """Select +/- radius siblings around hits without duplicating selected hits."""
    if radius <= 0:
        return []
    excluded = set(excluded_ids or set())
    by_parent: dict[str, list[RetrievedChunk]] = {}
    for chunk in siblings:
        if chunk.parent_id:
            by_parent.setdefault(chunk.parent_id, []).append(chunk)

    output: list[RetrievedChunk] = []
    for hit in hits:
        if not hit.parent_id:
            continue
        family = by_parent.get(hit.parent_id, [])
        family.sort(
            key=lambda c: (
                c.child_index is None,
                c.child_index if c.child_index is not None else 0,
                c.chunk_id,
            )
        )
        positions = {chunk.chunk_id: i for i, chunk in enumerate(family)}
        center = positions.get(hit.chunk_id)
        if center is None:
            continue
        for distance in range(1, radius + 1):
            for position in (center - distance, center + distance):
                if position < 0 or position >= len(family):
                    continue
                neighbor = family[position]
                if neighbor.chunk_id in excluded:
                    continue
                neighbor.retrieval_priority = 1
                neighbor.retrieval_rank = hit.retrieval_rank
                neighbor.score = hit.score
                output.append(neighbor)
                excluded.add(neighbor.chunk_id)
    return output


def _fetch_siblings(
    hits: list[RetrievedChunk],
    *,
    tenant_id: str,
    user_id: Optional[str],
    session_id: Optional[str],
) -> list[RetrievedChunk]:
    parent_ids = sorted({chunk.parent_id for chunk in hits if chunk.parent_id})
    conn = _dsn()
    if not conn or not parent_ids:
        return []
    where, params = _scope_sql(
        tenant_id=tenant_id, user_id=user_id, session_id=session_id
    )
    params.append(parent_ids)
    sql = f"""
        SELECT c.id::text, c.document_id::text, c.parent_id::text,
               c.content, c.title, c.page_number, c.source_url,
               c.token_estimate, c.tenant_id, c.session_id::text,
               coalesce(d.source_type, ''), c.metadata_json
        FROM document_chunks c
        LEFT JOIN documents d ON d.id = c.document_id
        WHERE {where} AND {_active_episode_sql()} AND c.parent_id = ANY(%s::uuid[])
        ORDER BY c.parent_id, c.created_at, c.id
    """
    try:
        import psycopg

        with psycopg.connect(conn) as connection:
            with connection.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
        siblings = [_chunk_from_row(row) for row in rows]
        # Existing rows may predate child_index metadata; stable query order is fallback.
        next_index: dict[str, int] = {}
        for chunk in siblings:
            if chunk.parent_id and chunk.child_index is None:
                chunk.child_index = next_index.get(chunk.parent_id, 0)
            if chunk.parent_id:
                next_index[chunk.parent_id] = max(
                    next_index.get(chunk.parent_id, 0), (chunk.child_index or 0) + 1
                )
        return siblings
    except Exception as exc:
        logger.warning("Neighbor expansion failed: %s", exc)
        return []


def pack_retrieval_candidates(
    primary: list[RetrievedChunk],
    neighbors: list[RetrievedChunk],
    supplemental: list[RetrievedChunk],
    *,
    token_budget: int,
) -> list[RetrievedChunk]:
    """Pack by primary hit > neighbor > low-ranked supplemental hit."""
    packed: list[RetrievedChunk] = []
    used = 0
    for bucket in (primary, neighbors, supplemental):
        for chunk in bucket:
            cost = max(1, int(chunk.token_estimate or 0))
            if used + cost > token_budget:
                continue
            packed.append(chunk)
            used += cost
    return packed


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
    fused = (
        calibrated_rrf_fuse(fts_ids, vec_ids, query)
        if fts_ids and vec_ids
        else rrf_fuse(lists)
    )
    # Optional rerank (fails open to RRF)
    try:
        from rag.rerank import maybe_rerank_ids

        fused_ids = maybe_rerank_ids(
            query, [cid for cid, _ in fused], top_k=len(fused)
        )
        ordered = fused_ids
        score_map = {cid: score for cid, score in fused}
    except Exception:
        ordered = [cid for cid, _ in fused]
        score_map = {cid: score for cid, score in fused}

    by_id = fetch_chunks_by_ids(ordered)
    candidates: list[RetrievedChunk] = []
    for rank, cid in enumerate(ordered):
        chunk = by_id.get(cid)
        if not chunk:
            continue
        # Enforce tenant filter in-process (defense in depth)
        if chunk.tenant_id and chunk.tenant_id != tenant_id:
            continue
        if session_id and chunk.session_id and chunk.session_id != str(session_id):
            continue
        chunk.score = float(score_map.get(cid, 0.0))
        chunk.retrieval_rank = rank
        candidates.append(chunk)

    primary, supplemental = diversify_chunks(
        candidates,
        top_k=top_k,
        max_children_per_parent=_env_int("RAG_MAX_CHILDREN_PER_PARENT", 2),
    )
    selected_hits = primary + supplemental
    radius = _env_nonnegative_int("RAG_NEIGHBOR_RADIUS", 1)
    siblings = _fetch_siblings(
        selected_hits,
        tenant_id=tenant_id,
        user_id=user_id,
        session_id=session_id,
    )
    neighbors = expand_neighbors_from_siblings(
        selected_hits,
        siblings,
        radius=radius,
        excluded_ids={chunk.chunk_id for chunk in selected_hits},
    )
    return pack_retrieval_candidates(
        primary,
        neighbors,
        supplemental,
        token_budget=_env_int("RAG_CONTEXT_TOKEN_BUDGET", 3500),
    )


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
        JOIN documents d ON d.id = c.document_id
        WHERE {where} AND {_active_episode_sql()} AND ({likes})
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
