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
            from gpt_researcher.memory.embeddings import create_memory_with_failover

            self._embeddings = create_memory_with_failover(
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
        if not query or not research_id:
            return []
        if self.ready:
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
                logger.warning(
                    "Vector search failed — trying keyword/FTS fallback: %s", exc
                )
                try:
                    from gpt_researcher.utils.dep_resilience import record_degradation

                    record_degradation(
                        "rag",
                        f"vector_search:{exc}"[:280],
                        rag_degraded=True,
                    )
                except Exception:
                    pass
        return self.keyword_search(query, research_id=research_id, k=k)

    def keyword_search(
        self,
        query: str,
        *,
        research_id: str,
        k: int = 8,
    ) -> list[Any]:
        """Keyword / PostgreSQL ILIKE fallback when embeddings are unavailable."""
        from gpt_researcher.utils.dep_resilience import (
            keyword_score,
            record_degradation,
            tokenize_query,
        )

        record_degradation("rag", "keyword_or_fts_fallback", rag_degraded=True)
        tokens = tokenize_query(query)
        docs = self._fts_or_ilike_search(research_id, tokens, k=k)
        if docs:
            return docs
        return []

    def _fts_or_ilike_search(
        self, research_id: str, tokens: list[str], *, k: int
    ) -> list[Any]:
        """Best-effort SQL keyword search against langchain_pg_embedding."""
        if not tokens:
            return []
        conn = (
            os.getenv("PGVECTOR_CONNECTION_STRING")
            or os.getenv("DATABASE_URL")
            or ""
        ).strip()
        if not conn:
            return []
        # Normalize to psycopg URL
        if conn.startswith("postgresql+asyncpg://"):
            conn = conn.replace("postgresql+asyncpg://", "postgresql://", 1)
        elif conn.startswith("postgresql+psycopg://"):
            conn = conn.replace("postgresql+psycopg://", "postgresql://", 1)
        try:
            import psycopg
            from langchain_core.documents import Document

            like_clauses = " OR ".join(["document ILIKE %s"] * min(len(tokens), 6))
            params: list[Any] = [research_id]
            params.extend([f"%{t}%" for t in tokens[:6]])
            sql = f"""
                SELECT document, cmetadata
                FROM langchain_pg_embedding
                WHERE cmetadata->>'research_id' = %s
                  AND ({like_clauses})
                LIMIT %s
            """
            params.append(max(k * 3, k))
            with psycopg.connect(conn) as connection:
                with connection.cursor() as cur:
                    cur.execute(sql, params)
                    rows = cur.fetchall()
            scored: list[tuple[int, Any]] = []
            for document, meta in rows:
                meta = meta or {}
                score = keyword_score(str(document or ""), tokens)
                scored.append(
                    (
                        score,
                        Document(page_content=str(document or ""), metadata=meta),
                    )
                )
            scored.sort(key=lambda x: x[0], reverse=True)
            return [doc for _, doc in scored[:k]]
        except Exception as exc:
            logger.debug("PG keyword/FTS fallback unavailable: %s", exc)
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
