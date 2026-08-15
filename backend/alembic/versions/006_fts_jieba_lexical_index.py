"""Store jieba-segmented lexical vectors instead of generated raw simple vectors.

Revision ID: 006_fts_jieba_lexical_index
Revises: 005_embedding_dim_1024
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "006_fts_jieba_lexical_index"
down_revision = "005_embedding_dim_1024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_chunks_content_tsv")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS content_tsv")
    op.add_column("document_chunks", sa.Column("content_tsv", postgresql.TSVECTOR(), nullable=True))
    op.execute("CREATE INDEX IF NOT EXISTS ix_chunks_content_tsv ON document_chunks USING GIN (content_tsv)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_chunks_content_tsv")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS content_tsv")
    op.execute("""
        ALTER TABLE document_chunks ADD COLUMN content_tsv tsvector
        GENERATED ALWAYS AS (to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(content, ''))) STORED
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_chunks_content_tsv ON document_chunks USING GIN (content_tsv)")
