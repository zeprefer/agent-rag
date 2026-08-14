import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Agent(TimestampMixin, Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False, index=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    default_knowledge_base_ids: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    chat_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    temperature: Mapped[float] = mapped_column(Float, default=0.2, nullable=False)
    top_k: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    max_context_tokens: Mapped[int] = mapped_column(Integer, default=3500, nullable=False)
    max_iterations: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    memory_window: Mapped[int] = mapped_column(Integer, default=12, nullable=False)
    enabled_tools: Mapped[list[str]] = mapped_column(
        JSONB,
        default=lambda: ["knowledge_search"],
        nullable=False,
    )
    require_citations: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    extra_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    tenant = relationship("Tenant")
