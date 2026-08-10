"""Knowledge-base-first source selection for reports requested from chat."""

from __future__ import annotations

import re
from typing import Any

from rag.retrieve import hybrid_retrieve

_FRESHNESS_RE = re.compile(
    r"(?:最新|当前|今天|近期|今年|本月|本周|实时|现状|价格|新闻|政策|法规|\b20\d{2}\b|latest|current|today|recent|news)",
    re.IGNORECASE,
)


def _is_prior_report_chunk(chunk: Any) -> bool:
    """Completed reports are ingested as uri=report:<session> for chat memory.

    They are secondary summaries, not primary citable sources. :-)
    """
    source_type = (getattr(chunk, "source_type", None) or "").strip().lower()
    source_url = (getattr(chunk, "source_url", None) or "").strip().lower()
    return source_type == "report" or source_url.startswith("report:")


def choose_report_sources(
    task: str, *, tenant_id: str, user_id: str | None, policy: str
) -> dict[str, Any]:
    """Retrieve private chunks first and choose local-only vs web research.

    This is intentionally deterministic. A current/freshness request always
    consults the web; otherwise local-only is allowed only with enough relevant
    evidence. Retrieval failure fails open to web, never to unscoped data.

    Prior generated reports (report:<id>) may help chat recall, but must not
    alone justify local-only report writing — citations would be untraceable.
    """
    if policy != "local_first":
        return {"mode": "web", "reason": "policy_web_first", "chunks": []}
    try:
        chunks = hybrid_retrieve(
            task,
            tenant_id=tenant_id,
            # Scope to owner; never drop filter for shared anonymous pool. :-)
            user_id=user_id,
            session_id=None,
            top_k=8,
        )
    except Exception:
        return {"mode": "web", "reason": "knowledge_retrieval_failed", "chunks": []}

    # Only primary private evidence (uploads / scraped pages) counts for
    # local-only reports. Prior report bodies are excluded from citation set.
    citable = [c for c in chunks if not _is_prior_report_chunk(c)]
    evidence_chars = sum(len(chunk.content or "") for chunk in citable)
    if _FRESHNESS_RE.search(task):
        mode, reason = "web", "freshness_requested"
    elif len(citable) >= 3 and evidence_chars >= 3000:
        mode, reason = "knowledge_base", "sufficient_private_evidence"
    else:
        mode, reason = "web", "insufficient_private_evidence"
    return {
        "mode": mode,
        "reason": reason,
        "chunks": citable if mode == "knowledge_base" else [],
        "chunk_count": len(citable),
        "evidence_chars": evidence_chars,
        "excluded_prior_reports": sum(1 for c in chunks if _is_prior_report_chunk(c)),
    }


def chunks_as_documents(chunks: list[Any]) -> list[Any]:
    """Expose selected child passages as scoped LangChain documents."""
    from langchain_core.documents import Document

    return [
        Document(
            page_content=chunk.content,
            metadata={
                "title": chunk.title or chunk.source_url or chunk.chunk_id,
                "source_title": chunk.title,
                "source_url": chunk.source_url,
                "chunk_id": chunk.chunk_id,
                "page_number": chunk.page_number,
            },
        )
        for chunk in chunks
        if getattr(chunk, "content", "") and not _is_prior_report_chunk(chunk)
    ]
