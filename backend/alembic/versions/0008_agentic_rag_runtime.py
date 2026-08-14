"""agentic RAG runtime configuration

Revision ID: 0008_agentic_rag_runtime
Revises: 0007_agent_configuration
Create Date: 2026-08-04 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_agentic_rag_runtime"
down_revision: str | None = "0007_agent_configuration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """为每个 Agent 增加工具循环、会话记忆和引用策略配置。"""
    op.add_column(
        "agents",
        sa.Column("max_iterations", sa.Integer(), nullable=False, server_default="4"),
    )
    op.add_column(
        "agents",
        sa.Column("memory_window", sa.Integer(), nullable=False, server_default="12"),
    )
    op.add_column(
        "agents",
        sa.Column(
            "enabled_tools",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[\"knowledge_search\"]'::jsonb"),
        ),
    )
    op.add_column(
        "agents",
        sa.Column("require_citations", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("agents", "require_citations")
    op.drop_column("agents", "enabled_tools")
    op.drop_column("agents", "memory_window")
    op.drop_column("agents", "max_iterations")
