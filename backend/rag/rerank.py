"""Optional reranker. Failures always fall back to RRF order."""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def rerank_enabled() -> bool:
    return (os.getenv("RAG_RERANKER_ENABLED") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def maybe_rerank_ids(query: str, chunk_ids: list[str], *, top_k: int) -> list[str]:
    """
    Reorder chunk ids with an external reranker (e.g. qwen3-rerank).

    When disabled or on any failure, return the original RRF order truncated.
    """
    if not chunk_ids:
        return []
    if not rerank_enabled():
        return chunk_ids[:top_k]

    try:
        # Pluggable hook — keep import local so missing deps never break chat
        provider = (os.getenv("RAG_RERANKER") or "").strip()
        if not provider:
            return chunk_ids[:top_k]
        # Future: call DashScope/Qwen rerank API with (query, passages)
        # For now, documented stub — fail open to RRF
        logger.info(
            "RAG reranker '%s' configured but not wired — using RRF order", provider
        )
        return chunk_ids[:top_k]
    except Exception as exc:
        logger.warning("Reranker failed — falling back to RRF: %s", exc)
        return chunk_ids[:top_k]
