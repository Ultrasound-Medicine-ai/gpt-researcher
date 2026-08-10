"""Retrieval helpers: legacy PGVector mirror + hybrid RAG."""

from gpt_researcher.vector_store.research_persist import (
    ResearchVectorStore,
    get_research_vector_store,
    is_vector_persist_enabled,
    maybe_persist_scraped_documents,
)

try:
    from rag.pipeline import retrieve_for_chat
    from rag.retrieve import hybrid_retrieve
except Exception:  # pragma: no cover
    retrieve_for_chat = None  # type: ignore
    hybrid_retrieve = None  # type: ignore

__all__ = [
    "ResearchVectorStore",
    "get_research_vector_store",
    "is_vector_persist_enabled",
    "maybe_persist_scraped_documents",
    "retrieve_for_chat",
    "hybrid_retrieve",
]
