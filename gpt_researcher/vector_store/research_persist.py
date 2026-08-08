"""
Session-scoped research chunk persistence (optional PGVector).

Quality invariant:
- Writes are best-effort and never raise into the research pipeline.
- The in-memory ContextCompressor path remains the source of truth for
  report generation; this module only mirrors chunks for later Chat/RAG.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

_COLLECTION = "research_chunks"
_store_singleton: Optional["ResearchVectorStore"] = None


def is_vector_persist_enabled() -> bool:
    return bool(os.getenv("DATABASE_URL") or os.getenv("PGVECTOR_CONNECTION_STRING"))


class ResearchVectorStore:
    def __init__(self) -> None:
        self._store = None
        self._embeddings = None
        self._ready = False
        self._init_store()

    def _init_store(self) -> None:
        if not is_vector_persist_enabled():
            return
        try:
            from gpt_researcher.config.config import Config
            from gpt_researcher.memory import Memory

            cfg = Config()
            self._embeddings = Memory(
                cfg.embedding_provider,
                cfg.embedding_model,
                **cfg.embedding_kwargs,
            ).get_embeddings()

            conn = (
                os.getenv("PGVECTOR_CONNECTION_STRING")
                or os.getenv("DATABASE_URL")
                or ""
            ).strip()
            if not conn:
                return
            if conn.startswith("postgresql+asyncpg://"):
                conn = conn.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
            elif conn.startswith("postgresql://"):
                conn = conn.replace("postgresql://", "postgresql+psycopg://", 1)

            try:
                from langchain_postgres import PGVector
            except ImportError:
                from langchain_community.vectorstores import PGVector  # type: ignore

            self._store = PGVector(
                embeddings=self._embeddings,
                collection_name=_COLLECTION,
                connection=conn,
                use_jsonb=True,
            )
            self._ready = True
            logger.info("ResearchVectorStore ready (PGVector)")
        except Exception as exc:
            logger.warning("ResearchVectorStore unavailable (non-fatal): %s", exc)
            self._store = None
            self._ready = False

    @property
    def ready(self) -> bool:
        return self._ready and self._store is not None

    def add_scraped_documents(
        self,
        research_id: str,
        documents: list[dict[str, Any]],
        *,
        source_index_start: int = 1,
    ) -> int:
        if not self.ready or not documents:
            return 0
        try:
            from langchain_core.documents import Document
            from langchain_text_splitters import RecursiveCharacterTextSplitter

            langchain_docs: list[Document] = []
            for offset, item in enumerate(documents):
                raw = str(item.get("raw_content") or "").strip()
                url = str(item.get("url") or "").strip()
                if not raw or not url:
                    continue
                title = str(item.get("title") or "")
                source_index = int(item.get("source_index") or (source_index_start + offset))
                tenant_id = str(
                    item.get("tenant_id")
                    or os.getenv("CURRENT_TENANT_ID")
                    or "anonymous"
                )
                langchain_docs.append(
                    Document(
                        page_content=raw,
                        metadata={
                            "research_id": research_id,
                            "url": url,
                            "title": title,
                            "source_index": source_index,
                            "tenant_id": tenant_id,
                        },
                    )
                )
            if not langchain_docs:
                return 0

            splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            chunks = splitter.split_documents(langchain_docs)
            for i, chunk in enumerate(chunks):
                chunk.metadata["chunk_index"] = i

            self._store.add_documents(chunks)
            return len(chunks)
        except Exception as exc:
            logger.warning("Vector persist failed (non-fatal): %s", exc)
            return 0

    def similarity_search(
        self,
        query: str,
        *,
        research_id: str,
        k: int = 8,
    ) -> list[Any]:
        if not self.ready or not query or not research_id:
            return []
        try:
            try:
                return self._store.similarity_search(
                    query, k=k, filter={"research_id": research_id}
                )
            except Exception:
                results = self._store.similarity_search(query, k=max(k * 3, 12))
                return [
                    doc
                    for doc in results
                    if (doc.metadata or {}).get("research_id") == research_id
                ][:k]
        except Exception as exc:
            logger.warning("Vector search failed (non-fatal): %s", exc)
            return []

    def format_context(self, docs: list[Any], max_chars: int = 12000) -> str:
        parts: list[str] = []
        total = 0
        for doc in docs:
            meta = getattr(doc, "metadata", {}) or {}
            header = f"[{meta.get('source_index', '?')}] {meta.get('title') or meta.get('url') or ''}"
            body = getattr(doc, "page_content", "") or ""
            block = f"{header}\n{body}"
            if total + len(block) > max_chars:
                break
            parts.append(block)
            total += len(block)
        return "\n\n".join(parts)


def get_research_vector_store() -> ResearchVectorStore:
    global _store_singleton
    if _store_singleton is None:
        _store_singleton = ResearchVectorStore()
    return _store_singleton


def maybe_persist_scraped_documents(research_id: str, documents: list[dict[str, Any]]) -> int:
    """Safe helper for research pipeline — never raises."""
    try:
        return get_research_vector_store().add_scraped_documents(research_id, documents)
    except Exception as exc:
        logger.debug("maybe_persist skipped: %s", exc)
        return 0
