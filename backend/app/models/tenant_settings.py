import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class TenantSettings(TimestampMixin, Base):
    __tablename__ = "tenant_settings"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        primary_key=True,
    )
    default_language: Mapped[str] = mapped_column(String(16), default="zh-CN", nullable=False)
    allowed_kb_file_extensions: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    max_upload_size_mb: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    max_chat_attachment_size_mb: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    rag_top_k: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    rag_temperature: Mapped[float] = mapped_column(Float, default=0.2, nullable=False)
    audit_log_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    security_scan_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    data_retention_days: Mapped[int] = mapped_column(Integer, default=365, nullable=False)
    extra_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    tenant = relationship("Tenant", back_populates="settings")
