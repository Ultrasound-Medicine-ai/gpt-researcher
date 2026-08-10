"""Ingest uploads / reports / chat into documents + parent/child chunks."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from rag.chunking import build_parent_child_chunks, content_checksum

logger = logging.getLogger(__name__)


def _as_uuid(value: Any) -> Optional[uuid.UUID]:
    if value is None or value == "":
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except Exception:
        return None


def _coerce_vector(vec: Any) -> Optional[list[float]]:
    """Accept only vectors matching EMBEDDING_DIM; else None (FTS-only). :-)"""
    if vec is None:
        return None
    try:
        from gpt_researcher.memory.embeddings import expected_embedding_dim

        values = list(vec)
        expected = expected_embedding_dim()
        if len(values) != expected:
            logger.warning(
                "Skipping embedding with dim=%s (expected %s)",
                len(values),
                expected,
            )
            return None
        return values
    except Exception:
        return None


async def _embed_texts(texts: list[str]) -> list[Optional[list[float]]]:
    if not texts:
        return []
    try:
        from gpt_researcher.config.config import Config
        from gpt_researcher.memory.embeddings import create_memory_with_failover

        cfg = Config()
        emb = create_memory_with_failover(
            cfg.embedding_provider,
            cfg.embedding_model,
            **cfg.embedding_kwargs,
        ).get_embeddings()
        # Batch when possible
        if hasattr(emb, "embed_documents"):
            try:
                vectors = emb.embed_documents(texts)
                return [_coerce_vector(v) for v in vectors]
            except Exception as exc:
                logger.warning("Batch embed failed, trying one-by-one: %s", exc)
        out: list[Optional[list[float]]] = []
        for t in texts:
            try:
                out.append(_coerce_vector(emb.embed_query(t)))
            except Exception:
                out.append(None)
        return out
    except Exception as exc:
        logger.warning("Embedding unavailable during ingest (FTS-only): %s", exc)
        try:
            from gpt_researcher.utils.dep_resilience import record_degradation

            record_degradation("rag", f"ingest_embed:{exc}"[:280], rag_degraded=True)
        except Exception:
            pass
        return [None] * len(texts)


async def ingest_text_document(
    *,
    text: str,
    title: str = "",
    uri: str = "",
    source_type: str = "upload",
    tenant_id: str = "anonymous",
    user_id: str = "anonymous",
    session_id: str | uuid.UUID | None = None,
    page_number: int | None = None,
    source_url: str = "",
    metadata: dict | None = None,
    replace_same_checksum: bool = True,
) -> Optional[str]:
    """
    Persist a document + parent/child chunks. Returns document_id or None.

    Never raises into caller — ingest is best-effort for report quality path.
    """
    text = (text or "").strip()
    if not text:
        return None
    try:
        from db.session import get_session_factory, is_db_enabled
        from db.models import Document, DocumentChunk

        if not is_db_enabled():
            return None
        factory = get_session_factory()
        if factory is None:
            return None

        sid = _as_uuid(session_id)
        checksum = content_checksum(text)
        drafts = build_parent_child_chunks(
            text,
            title=title,
            source_url=source_url or uri,
            page_number=page_number,
            extra_meta=metadata,
        )
        if not drafts:
            return None

        # Embed children preferentially (citeable); parents optional
        child_idxs = [i for i, d in enumerate(drafts) if d.chunk_level == "child"]
        child_vecs = await _embed_texts([drafts[i].content for i in child_idxs])
        vec_by_draft: dict[int, Optional[list[float]]] = {
            idx: child_vecs[j] for j, idx in enumerate(child_idxs)
        }

        async with factory() as session:
            from sqlalchemy import delete, select

            # documents.session_id has FK → research_sessions; chunks keep filter id even if FK missing
            doc_session_id = sid
            if sid is not None:
                from db.models import ResearchSession

                exists = (
                    await session.execute(
                        select(ResearchSession.id).where(ResearchSession.id == sid).limit(1)
                    )
                ).scalar_one_or_none()
                if exists is None:
                    logger.info(
                        "RAG ingest: session %s not in research_sessions — "
                        "document.session_id=NULL; chunks still scoped by session_id",
                        sid,
                    )
                    doc_session_id = None

            if replace_same_checksum and checksum:
                existing = (
                    await session.execute(
                        select(Document).where(
                            Document.tenant_id == tenant_id,
                            Document.user_id == user_id,
                            Document.checksum == checksum,
                            Document.source_type == source_type,
                            Document.uri == (uri or source_url or ""),
                        )
                    )
                ).scalars().first()
                if existing:
                    await session.execute(
                        delete(Document).where(Document.id == existing.id)
                    )

            doc = Document(
                id=uuid.uuid4(),
                tenant_id=tenant_id or "anonymous",
                user_id=user_id or "anonymous",
                session_id=doc_session_id,
                source_type=source_type,
                title=title or uri or source_type,
                uri=uri or source_url or "",
                checksum=checksum,
                metadata_json={
                    **(metadata or {}),
                    **({"research_id": str(sid)} if sid else {}),
                },
            )
            session.add(doc)
            await session.flush()

            id_by_draft_index: dict[int, uuid.UUID] = {}
            # Parents first
            for i, draft in enumerate(drafts):
                if draft.chunk_level != "parent":
                    continue
                cid = uuid.uuid4()
                id_by_draft_index[i] = cid
                session.add(
                    DocumentChunk(
                        id=cid,
                        document_id=doc.id,
                        parent_id=None,
                        chunk_level="parent",
                        content=draft.content,
                        title=draft.title,
                        page_number=draft.page_number,
                        source_url=draft.source_url,
                        token_estimate=draft.token_estimate,
                        tenant_id=doc.tenant_id,
                        user_id=doc.user_id,
                        session_id=sid,
                        metadata_json=draft.metadata,
                        embedding=None,
                    )
                )
            for i, draft in enumerate(drafts):
                if draft.chunk_level != "child":
                    continue
                parent_uuid = (
                    id_by_draft_index.get(draft.parent_index)
                    if draft.parent_index is not None
                    else None
                )
                session.add(
                    DocumentChunk(
                        id=uuid.uuid4(),
                        document_id=doc.id,
                        parent_id=parent_uuid,
                        chunk_level="child",
                        content=draft.content,
                        title=draft.title,
                        page_number=draft.page_number,
                        source_url=draft.source_url,
                        token_estimate=draft.token_estimate,
                        tenant_id=doc.tenant_id,
                        user_id=doc.user_id,
                        session_id=sid,
                        metadata_json=draft.metadata,
                        embedding=vec_by_draft.get(i),
                    )
                )
            await session.commit()
            logger.info(
                "RAG ingested document %s (%s) chunks=%s session=%s",
                doc.id,
                source_type,
                len(drafts),
                sid,
            )
            return str(doc.id)
    except Exception as exc:
        logger.warning("RAG ingest failed (non-fatal): %s", exc)
        return None


async def ingest_upload_file(
    *,
    file_path: str,
    filename: str,
    tenant_id: str,
    user_id: str,
    session_id: str | None = None,
) -> Optional[str]:
    try:
        from gpt_researcher.document.document import DocumentLoader

        loader = DocumentLoader([file_path])
        docs = await loader.load()
        parts = [str(d.get("raw_content") or "") for d in docs or []]
        text = "\n\n".join(p for p in parts if p.strip())
        if len(text.strip()) < 20:
            return None
        return await ingest_text_document(
            text=text,
            title=filename,
            uri=file_path,
            source_type="upload",
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            source_url=filename,
            metadata={"filename": filename},
        )
    except Exception as exc:
        logger.warning("Upload ingest skipped: %s", exc)
        return None
