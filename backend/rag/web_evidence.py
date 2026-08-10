"""Web scrape → PG Hybrid RAG → fixed-budget Evidence Pack for Writer. :-)"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)


def web_evidence_pack_enabled() -> bool:
    raw = (os.getenv("WEB_RAG_EVIDENCE_PACK") or "true").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def web_rag_context_budget_chars() -> int:
    raw = (os.getenv("WEB_RAG_CONTEXT_BUDGET") or "6000").strip()
    try:
        return max(1000, min(20000, int(raw)))
    except ValueError:
        return 6000


def rag_scope_from_headers(headers: Optional[dict]) -> dict[str, str]:
    h = headers or {}
    tenant = str(h.get("X-GPTR-Tenant-Id") or h.get("tenant_id") or "").strip()
    user = str(h.get("X-GPTR-User-Id") or h.get("user_id") or "anonymous").strip()
    session = str(h.get("X-GPTR-Session-Id") or h.get("session_id") or "").strip()
    return {"tenant_id": tenant, "user_id": user or "anonymous", "session_id": session}


def has_rag_scope(headers: Optional[dict]) -> bool:
    scope = rag_scope_from_headers(headers)
    return bool(scope["tenant_id"] and scope["session_id"])


def lightweight_scrape_preview(scraped_data: list[dict], *, max_chars: int = 1200) -> str:
    """Compress stand-in: titles + short excerpts, no embeddings. :-)"""
    parts: list[str] = []
    used = 0
    for doc in scraped_data or []:
        title = str(doc.get("title") or "").strip() or "Untitled"
        url = str(doc.get("url") or "").strip()
        body = str(doc.get("raw_content") or "").strip()
        if not body:
            continue
        excerpt = body[:400].rstrip()
        block = f"Source: {url}\nTitle: {title}\nContent: {excerpt}"
        if used + len(block) > max_chars and parts:
            break
        parts.append(block)
        used += len(block)
    return "\n\n".join(parts)


async def ingest_research_sources(
    sources: list[dict[str, Any]],
    *,
    tenant_id: str,
    user_id: str,
    session_id: str,
    job_id: str = "",
    agent_research_id: str = "",
) -> int:
    """Persist scraped pages as parent/child chunks. Returns ingest count. :-)"""
    try:
        from rag.ingest import ingest_text_document
    except Exception as exc:
        logger.warning("web_evidence ingest unavailable: %s", exc)
        return 0

    count = 0
    seen_uri: set[str] = set()
    for src in sources or []:
        body = str(src.get("raw_content") or src.get("excerpt") or "").strip()
        if len(body) < 40:
            continue
        quality = str(src.get("source_quality") or "").strip().lower()
        if quality in {"low", "failed", "skipped"}:
            continue
        url = str(src.get("url") or "").strip()
        uri = url or f"scrape:{hash(body) & 0xFFFFFFFF:x}"
        if uri in seen_uri:
            continue
        seen_uri.add(uri)
        try:
            doc_id = await ingest_text_document(
                text=body,
                title=str(src.get("title") or "")[:200],
                uri=uri,
                source_type="scrape",
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=session_id,
                source_url=url,
                metadata={
                    "job_id": job_id,
                    "agent_research_id": agent_research_id,
                    "web_evidence": True,
                },
                replace_same_checksum=True,
            )
            if doc_id:
                count += 1
        except Exception as exc:
            logger.debug("Skip scrape ingest for %s: %s", uri[:80], exc)
    return count


async def build_evidence_pack(
    query: str,
    *,
    tenant_id: str,
    user_id: str,
    session_id: str,
    top_k: int | None = None,
) -> tuple[str, int]:
    """Hybrid retrieve + budgeted pack. Returns (text, char_len). :-)"""
    from rag.context import assemble_evidence
    from rag.retrieve import hybrid_retrieve

    budget_chars = web_rag_context_budget_chars()
    k = top_k
    if k is None:
        raw = (os.getenv("WEB_RAG_TOP_K") or os.getenv("RAG_TOP_K") or "10").strip()
        try:
            k = max(4, min(20, int(raw)))
        except ValueError:
            k = 10

    chunks = hybrid_retrieve(
        query,
        tenant_id=tenant_id,
        user_id=user_id,
        session_id=session_id,
        top_k=k,
    )
    if not chunks:
        return "", 0

    # assemble_evidence budgets in tokens; map chars ≈ 2× tokens for CJK-heavy text. :-)
    token_budget = max(500, budget_chars // 2)
    assembled = assemble_evidence(chunks, token_budget=token_budget)
    block = (assembled.evidence_block or "").strip()
    if len(block) > budget_chars:
        block = block[:budget_chars].rstrip() + "\n…"
    return block, len(block)


async def apply_web_evidence_pack(researcher: Any) -> bool:
    """
    Ingest research_sources into PG, replace researcher.context with Evidence Pack.

    Keeps research_sources untouched for SourceRegistry citations.
    Returns True when context was replaced.
    """
    if not web_evidence_pack_enabled():
        return False

    scope = rag_scope_from_headers(getattr(researcher, "headers", None))
    if not scope["tenant_id"] or not scope["session_id"]:
        logger.info("Web Evidence Pack skipped: missing tenant/session in headers")
        return False

    sources = []
    try:
        sources = list(researcher.get_research_sources() or [])
    except Exception:
        sources = list(getattr(researcher, "research_sources", None) or [])

    if not sources:
        return False

    job_id = str((researcher.headers or {}).get("X-GPTR-Job-Id") or "")
    agent_rid = ""
    try:
        agent_rid = str(researcher._generate_research_id())
    except Exception:
        pass

    ingested = await ingest_research_sources(
        sources,
        tenant_id=scope["tenant_id"],
        user_id=scope["user_id"],
        session_id=scope["session_id"],
        job_id=job_id,
        agent_research_id=agent_rid,
    )
    logger.info(
        "Web Evidence Pack ingest: %s docs (session=%s)",
        ingested,
        scope["session_id"][:8],
    )

    query = str(getattr(researcher, "query", "") or "").strip()
    if not query:
        return False

    pack, pack_len = await build_evidence_pack(
        query,
        tenant_id=scope["tenant_id"],
        user_id=scope["user_id"],
        session_id=scope["session_id"],
    )
    if not pack:
        logger.warning("Web Evidence Pack retrieve empty — keeping compress context")
        return False

    prev_len = len(str(getattr(researcher, "context", "") or ""))
    researcher.context = pack
    logger.info(
        "Web Evidence Pack applied: context %s → %s chars (budget=%s)",
        prev_len,
        pack_len,
        web_rag_context_budget_chars(),
    )
    return True
