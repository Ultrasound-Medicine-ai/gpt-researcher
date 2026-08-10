"""Add research_usage_daily audit table.

Revision ID: 002
Revises: 001
Create Date: 2026-08-09
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "research_usage_daily" in inspector.get_table_names():
        return
    op.create_table(
        "research_usage_daily",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("searches", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("llm_calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("jobs_started", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("jobs_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "user_id", "usage_date", name="uq_research_usage_daily"
        ),
    )
    op.create_index(
        "ix_research_usage_daily_tenant_id", "research_usage_daily", ["tenant_id"]
    )
    op.create_index(
        "ix_research_usage_daily_user_id", "research_usage_daily", ["user_id"]
    )
    op.create_index(
        "ix_research_usage_daily_usage_date", "research_usage_daily", ["usage_date"]
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "research_usage_daily" not in inspector.get_table_names():
        return
    op.drop_index("ix_research_usage_daily_usage_date", table_name="research_usage_daily")
    op.drop_index("ix_research_usage_daily_user_id", table_name="research_usage_daily")
    op.drop_index("ix_research_usage_daily_tenant_id", table_name="research_usage_daily")
    op.drop_table("research_usage_daily")
