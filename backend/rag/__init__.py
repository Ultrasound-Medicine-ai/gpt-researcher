"""Session-scoped hybrid RAG (parent/child chunks, FTS + vector + RRF)."""

from rag.chunking import build_parent_child_chunks, estimate_tokens
from rag.ingest import ingest_text_document
from rag.pipeline import retrieve_for_chat
from rag.retrieve import hybrid_retrieve

__all__ = [
    "build_parent_child_chunks",
    "estimate_tokens",
    "ingest_text_document",
    "retrieve_for_chat",
    "hybrid_retrieve",
]
