"""Resize document_chunks.embedding to EMBEDDING_DIM (default 1024).

Revision ID: 005_embedding_dim_1024
Revises: 004_user_auth_fields
"""

from __future__ import annotations

import os
from typing import Sequence, Union

from alembic import op

revision: str = "005_embedding_dim_1024"
down_revision: Union[str, None] = "004_user_auth_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _dim(default: int = 1024) -> int:
    raw = (os.getenv("EMBEDDING_DIM") or str(default)).strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return default


def upgrade() -> None:
    dim = _dim(1024)
    op.execute("DROP INDEX IF EXISTS ix_chunks_embedding_hnsw")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding")
    op.execute(f"ALTER TABLE document_chunks ADD COLUMN embedding vector({dim})")
    # Recreate HNSW when enough rows exist; ignore if extension/index fails. :-)
    op.execute(
        """
        DO $$
        BEGIN
          BEGIN
            CREATE INDEX IF NOT EXISTS ix_chunks_embedding_hnsw
              ON document_chunks USING hnsw (embedding vector_cosine_ops);
          EXCEPTION WHEN OTHERS THEN
            NULL;
          END;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_chunks_embedding_hnsw")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE document_chunks ADD COLUMN embedding vector(1536)")
