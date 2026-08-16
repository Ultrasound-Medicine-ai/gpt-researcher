"""Privacy-scoped episodic chat memory built on existing RAG documents/chunks."""

from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

SOURCE_TYPE = "chat_episode"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int((os.getenv(name) or str(default)).strip()))
    except ValueError:
        return default


def _parse_time(value: object) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def episode_should_rollover(
    metadata: dict | None, *, now: datetime, topic_key: str = ""
) -> bool:
    """Roll only on inactive/expired episodes or a deterministic idle gap."""
    metadata = metadata or {}
    if metadata.get("episode_status") != "active":
        return True
    expires = _parse_time(metadata.get("expires_at"))
    if expires and expires <= now:
        return True
    previous_topic = str(metadata.get("topic_key") or "").strip().lower()
    incoming_topic = (topic_key or "").strip().lower()
    if previous_topic and incoming_topic and previous_topic != incoming_topic:
        return True
    last = _parse_time(metadata.get("last_accessed_at"))
    idle = timedelta(minutes=_env_int("EPISODE_MEMORY_IDLE_MINUTES", 45))
    return last is None or now - last > idle


def episode_metadata(*, episode_id: str, now: datetime, topic_key: str = "") -> dict:
    ttl_days = _env_int("EPISODE_MEMORY_TTL_DAYS", 30)
    return {
        "episode_id": episode_id,
        "episode_status": "active",
        "topic_key": topic_key[:160],
        "pinned": False,
        "access_count": 0,
        "child_count": 0,
        "created_at": now.isoformat(),
        "last_accessed_at": now.isoformat(),
        "expires_at": (now + timedelta(days=ttl_days)).isoformat(),
    }


def _turn_hash(role: str, content: str) -> str:
    return hashlib.sha256(f"{role}\0{content}".encode("utf-8")).hexdigest()


async def record_episode_turns(
    *,
    tenant_id: str,
    user_id: str,
    session_id: str,
    turns: Iterable[tuple[str, str]],
    topic_key: str = "",
) -> bool:
    """Append turns to the active episode. Fails closed on invalid ownership."""
    clean_turns = [
        (str(role), str(content).strip())
        for role, content in turns
        if str(content or "").strip() and str(role) in {"user", "assistant", "tool"}
    ]
    if not clean_turns:
        return False
    try:
        from sqlalchemy import func, select

        from db.models import Document, DocumentChunk, ResearchSession
        from db.session import get_session_factory, is_db_enabled
        from rag.chunking import estimate_tokens
        from rag.fts import fts_index_text
        from rag.ingest import _embed_texts

        if not is_db_enabled() or not (factory := get_session_factory()):
            return False
        sid = uuid.UUID(str(session_id))
        now = _utcnow()
        async with factory() as session:
            # Do not create memory for a session owned by somebody else.
            owner = (
                await session.execute(
                    select(ResearchSession.id).where(
                        ResearchSession.id == sid,
                        ResearchSession.tenant_id == tenant_id,
                        ResearchSession.user_id == user_id,
                    )
                )
            ).scalar_one_or_none()
            if owner is None:
                return False

            candidates = (
                await session.execute(
                    select(Document)
                    .where(
                        Document.source_type == SOURCE_TYPE,
                        Document.tenant_id == tenant_id,
                        Document.user_id == user_id,
                        Document.session_id == sid,
                    )
                    .order_by(Document.created_at.desc())
                )
            ).scalars().all()
            doc = next(
                (
                    item for item in candidates
                    if not episode_should_rollover(
                        item.metadata_json, now=now, topic_key=topic_key
                    )
                ),
                None,
            )
            if doc is None:
                meta = episode_metadata(episode_id=str(uuid.uuid4()), now=now, topic_key=topic_key)
                doc = Document(
                    id=uuid.uuid4(), tenant_id=tenant_id, user_id=user_id,
                    session_id=sid, source_type=SOURCE_TYPE,
                    title="Conversation episode", uri=f"episode:{meta['episode_id']}",
                    metadata_json=meta,
                )
                session.add(doc)
                await session.flush()
                parent = DocumentChunk(
                    id=uuid.uuid4(), document_id=doc.id, parent_id=None,
                    chunk_level="parent", content="", title="Conversation episode",
                    token_estimate=0, tenant_id=tenant_id, user_id=user_id,
                    session_id=sid, metadata_json={**meta, "role": "episode_parent"},
                )
                session.add(parent)
                await session.flush()
            else:
                parent = (
                    await session.execute(
                        select(DocumentChunk).where(
                            DocumentChunk.document_id == doc.id,
                            DocumentChunk.chunk_level == "parent",
                        )
                    )
                ).scalars().first()
                if parent is None:
                    return False

            metadata = dict(doc.metadata_json or {})
            last_child = (
                await session.execute(
                    select(DocumentChunk)
                    .where(DocumentChunk.parent_id == parent.id, DocumentChunk.chunk_level == "child")
                    .order_by(DocumentChunk.created_at.desc())
                    .limit(1)
                )
            ).scalars().first()
            child_count = int(metadata.get("child_count") or 0)
            texts = [f"{role}: {content}" for role, content in clean_turns]
            embed_enabled = (os.getenv("EPISODE_MEMORY_EMBEDDINGS", "true").strip().lower()
                             in {"1", "true", "yes", "on"})
            vectors = await _embed_texts(texts) if embed_enabled else [None] * len(texts)
            for (role, content), text, vector in zip(clean_turns, texts, vectors):
                digest = _turn_hash(role, content)
                if last_child and (last_child.metadata_json or {}).get("turn_hash") == digest:
                    continue  # idempotent retry of the most recent turn
                session.add(
                    DocumentChunk(
                        id=uuid.uuid4(), document_id=doc.id, parent_id=parent.id,
                        chunk_level="child", content=text, title="Conversation memory",
                        token_estimate=estimate_tokens(text), tenant_id=tenant_id,
                        user_id=user_id, session_id=sid,
                        metadata_json={
                            "role": role, "child_index": child_count,
                            "episode_id": metadata.get("episode_id"), "turn_hash": digest,
                        },
                        embedding=vector,
                        content_tsv=func.to_tsvector("simple", fts_index_text(text)),
                    )
                )
                child_count += 1
                last_child = None

            metadata.update({
                "episode_status": "active", "topic_key": (topic_key or metadata.get("topic_key") or "")[:160],
                "child_count": child_count,
                "access_count": int(metadata.get("access_count") or 0) + 1,
                "last_accessed_at": now.isoformat(),
            })
            doc.metadata_json = metadata
            parent.metadata_json = {**metadata, "role": "episode_parent"}
            await session.commit()
        await maintain_episode_lifecycle(tenant_id=tenant_id, user_id=user_id)
        return True
    except Exception:
        return False


async def maintain_episode_lifecycle(*, tenant_id: str, user_id: str) -> None:
    """Archive inactive episodes and purge expired ones within one user's scope."""
    try:
        from sqlalchemy import delete, select

        from db.models import Document, DocumentChunk
        from db.session import get_session_factory, is_db_enabled

        if not is_db_enabled() or not (factory := get_session_factory()):
            return
        now = _utcnow()
        max_active = _env_int("EPISODE_MEMORY_MAX_ACTIVE", 20)
        purge_after = timedelta(days=_env_int("EPISODE_MEMORY_PURGE_AFTER_DAYS", 7))
        async with factory() as session:
            docs = (
                await session.execute(
                    select(Document).where(
                        Document.source_type == SOURCE_TYPE,
                        Document.tenant_id == tenant_id,
                        Document.user_id == user_id,
                    )
                )
            ).scalars().all()
            active: list[Document] = []
            for doc in docs:
                meta = dict(doc.metadata_json or {})
                expires = _parse_time(meta.get("expires_at"))
                if meta.get("episode_status") == "expired" and expires and now - expires > purge_after:
                    await session.execute(delete(Document).where(Document.id == doc.id))
                    continue
                if expires and expires <= now and not meta.get("pinned"):
                    meta["episode_status"] = "expired"
                    doc.metadata_json = meta
                    parent = (
                        await session.execute(
                            select(DocumentChunk).where(
                                DocumentChunk.document_id == doc.id,
                                DocumentChunk.chunk_level == "parent",
                            )
                        )
                    ).scalars().first()
                    if parent:
                        parent.metadata_json = {**meta, "role": "episode_parent"}
                    continue
                if meta.get("episode_status", "active") == "active" and not meta.get("pinned"):
                    active.append(doc)
            active.sort(key=lambda item: _parse_time((item.metadata_json or {}).get("last_accessed_at")) or item.created_at)
            for doc in active[:-max_active] if len(active) > max_active else []:
                meta = dict(doc.metadata_json or {})
                meta["episode_status"] = "archived"
                doc.metadata_json = meta
                parent = (
                    await session.execute(
                        select(DocumentChunk).where(
                            DocumentChunk.document_id == doc.id,
                            DocumentChunk.chunk_level == "parent",
                        )
                    )
                ).scalars().first()
                if parent:
                    parent.metadata_json = {**meta, "role": "episode_parent"}
            await session.commit()
    except Exception:
        return
