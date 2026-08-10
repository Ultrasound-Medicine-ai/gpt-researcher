"""Research job reliability columns, indexes, and idempotency constraint.

Revision ID: 001
Revises:
Create Date: 2026-08-09

Creates base SaaS tables on empty databases, then ensures ResearchJob
reliability columns + unique idempotency index exist for upgrades.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_JSON_TYPE = postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def _table_exists(inspector: sa.Inspector, name: str) -> bool:
    return name in inspector.get_table_names()


def _column_names(inspector: sa.Inspector, table: str) -> set[str]:
    return {col["name"] for col in inspector.get_columns(table)}


def _index_names(inspector: sa.Inspector, table: str) -> set[str]:
    return {idx["name"] for idx in inspector.get_indexes(table)}


def _ensure_base_tables() -> None:
    """Create all ORM tables on empty DBs (idempotent via create_all)."""
    from db.models import Base

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def upgrade() -> None:
    _ensure_base_tables()

    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "research_jobs"):
        # Should already exist via create_all; leave a safety net.
        op.create_table(
            "research_jobs",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("user_id", sa.String(length=64), nullable=False, server_default="anonymous"),
            sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="anonymous"),
            sa.Column(
                "status",
                sa.String(length=32),
                nullable=False,
                server_default="pending_dispatch",
            ),
            sa.Column("stage", sa.String(length=32), nullable=False, server_default="planning"),
            sa.Column("progress", sa.Text(), nullable=False, server_default=""),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("payload", _JSON_TYPE, nullable=True),
            sa.Column("result", _JSON_TYPE, nullable=True),
            sa.Column("attempt", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("idempotency_key", sa.String(length=128), nullable=True),
            sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("enqueued_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("worker_id", sa.String(length=128), nullable=True),
            sa.Column("last_error_code", sa.String(length=64), nullable=True),
            sa.Column("checkpoint_json", _JSON_TYPE, nullable=True),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.ForeignKeyConstraint(["session_id"], ["research_sessions.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
    else:
        existing = _column_names(inspector, "research_jobs")
        additions = [
            ("stage", sa.Column("stage", sa.String(length=32), server_default="planning")),
            ("heartbeat_at", sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True)),
            ("started_at", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True)),
            ("finished_at", sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True)),
            ("enqueued_at", sa.Column("enqueued_at", sa.DateTime(timezone=True), nullable=True)),
            ("next_retry_at", sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True)),
            (
                "cancel_requested_at",
                sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True),
            ),
            ("worker_id", sa.Column("worker_id", sa.String(length=128), nullable=True)),
            ("last_error_code", sa.Column("last_error_code", sa.String(length=64), nullable=True)),
            ("checkpoint_json", sa.Column("checkpoint_json", _JSON_TYPE, nullable=True)),
            ("version", sa.Column("version", sa.Integer(), server_default="1")),
            ("idempotency_key", sa.Column("idempotency_key", sa.String(length=128), nullable=True)),
        ]
        for name, column in additions:
            if name not in existing:
                op.add_column("research_jobs", column)

    inspector = sa.inspect(bind)
    indexes = _index_names(inspector, "research_jobs")

    if "ix_research_jobs_status" not in indexes:
        op.create_index("ix_research_jobs_status", "research_jobs", ["status"], unique=False)
    if "ix_research_jobs_next_retry_at" not in indexes:
        op.create_index(
            "ix_research_jobs_next_retry_at", "research_jobs", ["next_retry_at"], unique=False
        )
    if "ix_research_jobs_heartbeat_at" not in indexes:
        op.create_index(
            "ix_research_jobs_heartbeat_at", "research_jobs", ["heartbeat_at"], unique=False
        )
    if "uq_research_jobs_tenant_user_idempotency" not in indexes:
        op.create_index(
            "uq_research_jobs_tenant_user_idempotency",
            "research_jobs",
            ["tenant_id", "user_id", "idempotency_key"],
            unique=True,
            postgresql_where=sa.text("idempotency_key IS NOT NULL"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _table_exists(inspector, "research_jobs"):
        return

    indexes = _index_names(inspector, "research_jobs")
    for name in (
        "uq_research_jobs_tenant_user_idempotency",
        "ix_research_jobs_heartbeat_at",
        "ix_research_jobs_next_retry_at",
        "ix_research_jobs_status",
    ):
        if name in indexes:
            op.drop_index(name, table_name="research_jobs")

    existing = _column_names(inspector, "research_jobs")
    for name in (
        "checkpoint_json",
        "last_error_code",
        "worker_id",
        "cancel_requested_at",
        "next_retry_at",
        "enqueued_at",
        "finished_at",
        "started_at",
        "heartbeat_at",
    ):
        if name in existing:
            op.drop_column("research_jobs", name)
