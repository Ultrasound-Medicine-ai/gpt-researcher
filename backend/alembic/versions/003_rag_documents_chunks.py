"""RAG documents + document_chunks (parent/child) with FTS + pgvector.

Revision ID: 003
Revises: 002
Create Date: 2026-08-09
"""

from __future__ import annotations

import os
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_JSON = postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")
_EMBED_DIM = int(os.getenv("EMBEDDING_DIM", "1536"))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # pgvector extension (no-op if already present)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    if "documents" not in inspector.get_table_names():
        op.create_table(
            "documents",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("tenant_id", sa.String(length=64), nullable=False),
            sa.Column("user_id", sa.String(length=64), nullable=False),
            sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("source_type", sa.String(length=32), nullable=False),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("uri", sa.Text(), nullable=False),
            sa.Column("checksum", sa.String(length=64), nullable=True),
            sa.Column("metadata_json", _JSON, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["session_id"], ["research_sessions.id"], ondelete="SET NULL"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_documents_tenant_id", "documents", ["tenant_id"])
        op.create_index("ix_documents_user_id", "documents", ["user_id"])
        op.create_index("ix_documents_session_id", "documents", ["session_id"])
        op.create_index("ix_documents_checksum", "documents", ["checksum"])
        op.create_index(
            "ix_documents_tenant_session", "documents", ["tenant_id", "session_id"]
        )
        op.create_index(
            "ix_documents_tenant_user", "documents", ["tenant_id", "user_id"]
        )

    inspector = sa.inspect(bind)
    if "document_chunks" not in inspector.get_table_names():
        op.create_table(
            "document_chunks",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("chunk_level", sa.String(length=16), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("page_number", sa.Integer(), nullable=True),
            sa.Column("source_url", sa.Text(), nullable=False),
            sa.Column("token_estimate", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("tenant_id", sa.String(length=64), nullable=False),
            sa.Column("user_id", sa.String(length=64), nullable=False),
            sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("metadata_json", _JSON, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["parent_id"], ["document_chunks.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.execute(
            f"ALTER TABLE document_chunks ADD COLUMN embedding vector({_EMBED_DIM})"
        )
        op.create_index("ix_chunks_tenant_id", "document_chunks", ["tenant_id"])
        op.create_index("ix_chunks_user_id", "document_chunks", ["user_id"])
        op.create_index("ix_chunks_session_id", "document_chunks", ["session_id"])
        op.create_index(
            "ix_chunks_tenant_session", "document_chunks", ["tenant_id", "session_id"]
        )
        op.create_index(
            "ix_chunks_document_level", "document_chunks", ["document_id", "chunk_level"]
        )
        op.create_index("ix_chunks_parent_id", "document_chunks", ["parent_id"])

        # Full-text search generated column + GIN
        op.execute(
            """
            ALTER TABLE document_chunks
            ADD COLUMN IF NOT EXISTS content_tsv tsvector
            GENERATED ALWAYS AS (
              to_tsvector(
                'simple',
                coalesce(title, '') || ' ' || coalesce(content, '')
              )
            ) STORED
            """
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_chunks_content_tsv "
            "ON document_chunks USING GIN (content_tsv)"
        )
        # ANN index — skip quietly if pgvector build lacks hnsw
        op.execute(
            """
            DO $$ BEGIN
              CREATE INDEX IF NOT EXISTS ix_chunks_embedding_hnsw
              ON document_chunks USING hnsw (embedding vector_cosine_ops);
            EXCEPTION WHEN OTHERS THEN
              RAISE NOTICE 'hnsw index skipped: %', SQLERRM;
            END $$;
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "document_chunks" in inspector.get_table_names():
        op.drop_table("document_chunks")
    if "documents" in inspector.get_table_names():
        op.drop_table("documents")
