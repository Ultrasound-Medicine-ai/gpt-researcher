"""High-level RAG retrieve + assemble for Chat."""

from __future__ import annotations

import logging
from typing import Any, Optional

from rag.context import AssembledContext, build_full_context
from rag.retrieve import hybrid_retrieve

logger = logging.getLogger(__name__)


def retrieve_for_chat(
    query: str,
    *,
    tenant_id: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    messages: Optional[list[dict]] = None,
    base_context: str = "",
) -> AssembledContext:
    """
    Hybrid retrieve under tenant/session scope, assemble context + citations.

    Cross-tenant leakage is prevented by SQL filters + in-process checks.
    """
    messages = messages or []
    rag_degraded = False
    children = []
    try:
        children = hybrid_retrieve(
            query,
            tenant_id=tenant_id or "anonymous",
            user_id=user_id,
            session_id=session_id,
        )
    except Exception as exc:
        logger.warning("hybrid_retrieve failed: %s", exc)
        rag_degraded = True

    if not children:
        rag_degraded = True

    assembled = build_full_context(
        messages=messages,
        children=children,
        base_context=base_context,
        rag_degraded=rag_degraded,
    )
    return assembled


def citations_as_metadata(ctx: AssembledContext) -> list[dict[str, Any]]:
    return [
        {
            "chunk_id": c.chunk_id,
            "title": c.title,
            "page_number": c.page_number,
            "source_url": c.source_url,
            "excerpt": c.excerpt,
        }
        for c in ctx.citations
    ]
