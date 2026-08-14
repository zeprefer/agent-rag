"""agent configuration
建 Agent 配置表
Revision ID: 0007_agent_configuration
Revises: 0006_rbac_audit_tenant_settings
Create Date: 2026-07-17 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_agent_configuration"
down_revision: str | None = "0006_rbac_audit_tenant_settings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("default_knowledge_base_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("chat_model", sa.String(length=120), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=False, server_default="0.2"),
        sa.Column("top_k", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("max_context_tokens", sa.Integer(), nullable=False, server_default="3500"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agents_tenant_id", "agents", ["tenant_id"])
    op.create_index("ix_agents_status", "agents", ["status"])

    '''这一列将聊天会话和 Agent 配置关联起来，使得每个聊天会话可以指定使用哪个 Agent（不同的 Agent 有不同的系统提示词、知识库、模型参数等）。
    这就是第 0007 号迁移 "Agent Configuration" 的核心功能——让用户可以选择不同的 Agent 进行对话。
    '''
    op.add_column("chat_sessions", sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_chat_sessions_agent_id_agents",
        "chat_sessions",
        "agents",
        ["agent_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_chat_sessions_agent_id", "chat_sessions", ["agent_id"])


def downgrade() -> None:
    op.drop_index("ix_chat_sessions_agent_id", table_name="chat_sessions")
    op.drop_constraint("fk_chat_sessions_agent_id_agents", "chat_sessions", type_="foreignkey")
    op.drop_column("chat_sessions", "agent_id")
    op.drop_index("ix_agents_status", table_name="agents")
    op.drop_index("ix_agents_tenant_id", table_name="agents")
    op.drop_table("agents")
