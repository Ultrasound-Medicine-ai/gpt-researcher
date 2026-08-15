"""SQLAlchemy models for small-scale multi-user SaaS persistence."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

import os

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# Use JSONB on PostgreSQL, JSON elsewhere
JsonType = JSON().with_variant(JSONB(), "postgresql")

try:
    from pgvector.sqlalchemy import Vector as _PgVector

    EmbeddingVector = _PgVector(int(os.getenv("EMBEDDING_DIM", "1024")))
except Exception:  # pragma: no cover - tests without pgvector
    EmbeddingVector = JsonType


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str | None] = mapped_column(String(320), unique=True, nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    kind: Mapped[str] = mapped_column(String(32), default="visitor")
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    sessions: Mapped[list["ResearchSession"]] = relationship(back_populates="user")


class ResearchSession(Base):
    __tablename__ = "research_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, default="anonymous")
    task_text: Mapped[str] = mapped_column(Text, default="")
    report_language: Mapped[str] = mapped_column(String(32), default="chinese")
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    job_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    user: Mapped["User"] = relationship(back_populates="sessions")
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    sources: Mapped[list["ResearchSource"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    report: Mapped["Report | None"] = relationship(
        back_populates="session", uselist=False, cascade="all, delete-orphan"
    )
    jobs: Mapped[list["ResearchJob"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_sessions.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text, default="")
    metadata_json: Mapped[dict | None] = mapped_column(JsonType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    session: Mapped["ResearchSession"] = relationship(back_populates="messages")


class ResearchSource(Base):
    __tablename__ = "research_sources"
    __table_args__ = (UniqueConstraint("session_id", "source_index", name="uq_session_source_index"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_sessions.id", ondelete="CASCADE"), index=True
    )
    source_index: Mapped[int] = mapped_column(Integer)
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text, default="")
    excerpt: Mapped[str] = mapped_column(Text, default="")
    raw_content_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    session: Mapped["ResearchSession"] = relationship(back_populates="sources")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_sessions.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    markdown: Mapped[str] = mapped_column(Text, default="")
    question: Mapped[str] = mapped_column(Text, default="")
    ordered_data: Mapped[list | None] = mapped_column(JsonType, nullable=True)
    citation_style: Mapped[str] = mapped_column(String(32), default="numbered")
    version: Mapped[int] = mapped_column(Integer, default=1)
    object_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    session: Mapped["ResearchSession"] = relationship(back_populates="report")


class ResearchJob(Base):
    __tablename__ = "research_jobs"
    __table_args__ = (
        Index("ix_research_jobs_status", "status"),
        Index("ix_research_jobs_next_retry_at", "next_retry_at"),
        Index("ix_research_jobs_heartbeat_at", "heartbeat_at"),
        Index(
            "uq_research_jobs_tenant_user_idempotency",
            "tenant_id",
            "user_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_sessions.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[str] = mapped_column(String(64), index=True, default="anonymous")
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, default="anonymous")
    status: Mapped[str] = mapped_column(String(32), default="pending_dispatch")
    stage: Mapped[str] = mapped_column(String(32), default="planning")
    progress: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict | None] = mapped_column(JsonType, nullable=True)
    result: Mapped[dict | None] = mapped_column(JsonType, nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    enqueued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    worker_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    checkpoint_json: Mapped[dict | None] = mapped_column(JsonType, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    session: Mapped["ResearchSession | None"] = relationship(back_populates="jobs")


class ResearchUsageDaily(Base):
    """Auditable per-user daily usage aggregates (UTC calendar day)."""

    __tablename__ = "research_usage_daily"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "user_id", "usage_date", name="uq_research_usage_daily"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, default="anonymous")
    user_id: Mapped[str] = mapped_column(String(64), index=True, default="anonymous")
    usage_date: Mapped[date] = mapped_column(Date, index=True)
    searches: Mapped[int] = mapped_column(Integer, default=0)
    llm_calls: Mapped[int] = mapped_column(Integer, default=0)
    jobs_started: Mapped[int] = mapped_column(Integer, default=0)
    jobs_completed: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class Document(Base):
    """Ingested source document (upload / report / chat / scrape)."""

    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_tenant_session", "tenant_id", "session_id"),
        Index("ix_documents_tenant_user", "tenant_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, default="anonymous")
    user_id: Mapped[str] = mapped_column(String(64), index=True, default="anonymous")
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(String(32), default="upload")  # upload|report|chat|scrape
    title: Mapped[str] = mapped_column(Text, default="")
    uri: Mapped[str] = mapped_column(Text, default="")  # file path / URL / report:session
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    metadata_json: Mapped[dict | None] = mapped_column(JsonType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentChunk(Base):
    """Parent (section) or child (citeable paragraph) chunk for hybrid RAG."""

    __tablename__ = "document_chunks"
    __table_args__ = (
        Index("ix_chunks_tenant_session", "tenant_id", "session_id"),
        Index("ix_chunks_document_level", "document_id", "chunk_level"),
        Index("ix_chunks_parent_id", "parent_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=True
    )
    chunk_level: Mapped[str] = mapped_column(String(16), default="child")  # parent|child
    content: Mapped[str] = mapped_column(Text, default="")
    content_tsv: Mapped[Any | None] = mapped_column(TSVECTOR, nullable=True)
    title: Mapped[str] = mapped_column(Text, default="")
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_url: Mapped[str] = mapped_column(Text, default="")
    token_estimate: Mapped[int] = mapped_column(Integer, default=0)
    # Denormalized filters (must match document scope)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, default="anonymous")
    user_id: Mapped[str] = mapped_column(String(64), index=True, default="anonymous")
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    metadata_json: Mapped[dict | None] = mapped_column(JsonType, nullable=True)
    embedding: Mapped[list | None] = mapped_column(EmbeddingVector, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    document: Mapped["Document"] = relationship(back_populates="chunks")
