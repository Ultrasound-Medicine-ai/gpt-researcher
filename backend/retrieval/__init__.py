"""Re-export research vector helpers for backend Chat enrichment."""

from gpt_researcher.vector_store.research_persist import (
    ResearchVectorStore,
    get_research_vector_store,
    is_vector_persist_enabled,
    maybe_persist_scraped_documents,
)

__all__ = [
    "ResearchVectorStore",
    "get_research_vector_store",
    "is_vector_persist_enabled",
    "maybe_persist_scraped_documents",
]
