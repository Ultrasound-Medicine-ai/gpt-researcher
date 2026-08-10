"""Per-section hybrid retrieve + Evidence extraction with quote verification."""

from __future__ import annotations

import logging
import re
from typing import Any, Callable, Optional

from trusted_report.flags import env_int
from trusted_report.llm import call_llm_json
from trusted_report.models import EvidenceItem, OutlineSection, as_str_list
from trusted_report import prompts

logger = logging.getLogger(__name__)

_WS = re.compile(r"\s+")

# LLM sometimes returns Chinese labels instead of numeric scores. :-)
_RELEVANCE_LABELS = {
    "直接相关": 1.0,
    "高度相关": 0.9,
    "相关": 0.7,
    "部分相关": 0.5,
    "弱相关": 0.3,
    "不相关": 0.0,
    "无关": 0.0,
}


def normalize_text(text: str) -> str:
    return _WS.sub(" ", (text or "").strip())


def parse_relevance(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float)):
        return max(0.0, min(1.0, float(value)))
    text = str(value).strip()
    try:
        return max(0.0, min(1.0, float(text)))
    except ValueError:
        pass
    if text in _RELEVANCE_LABELS:
        return _RELEVANCE_LABELS[text]
    for label, score in _RELEVANCE_LABELS.items():
        if label in text:
            return score
    return 0.0


def quote_in_source(quote: str, source: str) -> bool:
    q = normalize_text(quote)
    s = normalize_text(source)
    if len(q) < 8:
        return False
    return q in s


def passages_from_chunks(chunks: list[Any], *, token_budget: int) -> list[dict[str, Any]]:
    """Build limited Child passages with Parent ids; truncate by rough token budget."""
    used = 0
    out: list[dict[str, Any]] = []
    for ch in chunks:
        content = getattr(ch, "content", "") or ""
        est = max(1, len(content) // 4)
        if used + est > token_budget and out:
            break
        if est > token_budget and not out:
            content = content[: token_budget * 4]
            est = token_budget
        out.append(
            {
                "chunk_id": getattr(ch, "chunk_id", ""),
                "parent_chunk_id": getattr(ch, "parent_id", None) or "",
                "document_id": getattr(ch, "document_id", ""),
                "title": getattr(ch, "title", "") or "",
                "url": getattr(ch, "source_url", "") or "",
                "page": getattr(ch, "page_number", None),
                "content": content,
                "tenant_id": getattr(ch, "tenant_id", "") or "",
                "session_id": getattr(ch, "session_id", None),
            }
        )
        used += est
    return out


def verify_and_bind_evidence(
    raw_items: list[dict[str, Any]],
    passages: list[dict[str, Any]],
    *,
    tenant_id: str,
    session_id: Optional[str],
) -> tuple[list[EvidenceItem], int]:
    """
    Keep only evidence whose quote appears in the matching chunk content
    and whose scope matches tenant/session.
    Returns (items, cross_scope_violations).
    """
    by_id = {p["chunk_id"]: p for p in passages if p.get("chunk_id")}
    ok: list[EvidenceItem] = []
    cross_scope = 0
    for i, raw in enumerate(raw_items):
        cid = str(raw.get("chunk_id") or "")
        passage = by_id.get(cid)
        if not passage:
            continue
        if passage.get("tenant_id") and passage["tenant_id"] != tenant_id:
            cross_scope += 1
            continue
        if session_id and passage.get("session_id") and str(passage["session_id"]) != str(session_id):
            cross_scope += 1
            continue
        quote = str(raw.get("quote") or "")
        if not quote_in_source(quote, passage.get("content") or ""):
            continue
        eid = str(raw.get("evidence_id") or f"ev_{i+1:03d}")
        ok.append(
            EvidenceItem(
                evidence_id=eid,
                chunk_id=cid,
                parent_chunk_id=str(
                    raw.get("parent_chunk_id") or passage.get("parent_chunk_id") or ""
                ),
                quote=quote,
                source_title=str(raw.get("source_title") or passage.get("title") or ""),
                url=str(raw.get("url") or passage.get("url") or ""),
                page=raw.get("page") if raw.get("page") is not None else passage.get("page"),
                published_at=str(raw.get("published_at") or ""),
                source_quality=str(raw.get("source_quality") or ""),
                supports=as_str_list(raw.get("supports")),
                relevance=parse_relevance(raw.get("relevance")),
                document_id=str(passage.get("document_id") or ""),
                tenant_id=tenant_id,
                session_id=str(session_id) if session_id else None,
            )
        )
    return ok, cross_scope


def retrieve_section_chunks(
    section: OutlineSection,
    *,
    tenant_id: str,
    user_id: Optional[str],
    session_id: Optional[str],
    retrieve_fn: Optional[Callable[..., list]] = None,
) -> list[Any]:
    queries = list(section.search_queries or []) + list(section.questions_to_answer or [])
    if not queries:
        queries = [section.title]
    retrieve_fn = retrieve_fn or _default_retrieve
    seen: set[str] = set()
    merged: list[Any] = []
    top_k = env_int("TRUSTED_SECTION_TOP_K", 8)
    for q in queries[:6]:
        hits = retrieve_fn(
            q,
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            top_k=top_k,
        ) or []
        for h in hits:
            cid = getattr(h, "chunk_id", None)
            if cid and cid in seen:
                continue
            if cid:
                seen.add(cid)
            merged.append(h)
    return merged


def _default_retrieve(query: str, **kwargs):
    from rag.retrieve import hybrid_retrieve

    return hybrid_retrieve(query, **kwargs)


async def extract_section_evidence(
    section: OutlineSection,
    *,
    tenant_id: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    retrieve_fn: Optional[Callable[..., list]] = None,
    llm_call: Optional[Callable[..., Any]] = None,
) -> tuple[list[EvidenceItem], int, list[dict[str, Any]]]:
    chunks = retrieve_section_chunks(
        section,
        tenant_id=tenant_id,
        user_id=user_id,
        session_id=session_id,
        retrieve_fn=retrieve_fn,
    )
    budget = env_int("TRUSTED_SECTION_EVIDENCE_TOKEN_BUDGET", 1800, minimum=200)
    passages = passages_from_chunks(chunks, token_budget=budget)
    if not passages:
        return [], 0, []

    raw_list: list[dict[str, Any]] = []
    try:
        data = await call_llm_json(
            system=prompts.evidence_system(),
            user=prompts.evidence_user(
                section_id=section.section_id,
                questions=section.questions_to_answer or [section.title],
                passages=passages,
            ),
            llm_call=llm_call,
        )
        raw_list = list(data.get("evidence") or [])
    except Exception as exc:
        logger.warning("Evidence LLM failed — empty evidence: %s", exc)
        raw_list = []

    items, cross = verify_and_bind_evidence(
        raw_list, passages, tenant_id=tenant_id, session_id=session_id
    )
    return items, cross, passages
