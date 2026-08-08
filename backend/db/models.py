"""SQLAlchemy models for small-scale multi-user SaaS persistence."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# Use JSONB on PostgreSQL, JSON elsewhere
JsonType = JSON().with_variant(JSONB(), "postgresql")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str | None] = mapped_column(String(320), unique=True, nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
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

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_sessions.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[str] = mapped_column(String(64), index=True, default="anonymous")
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, default="anonymous")
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    progress: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict | None] = mapped_column(JsonType, nullable=True)
    result: Mapped[dict | None] = mapped_column(JsonType, nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    session: Mapped["ResearchSession | None"] = relationship(back_populates="jobs")
