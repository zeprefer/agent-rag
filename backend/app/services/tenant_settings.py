from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.tenant_settings import TenantSettings


def get_or_create_tenant_settings(db: Session, *, tenant_id) -> TenantSettings:
    tenant_settings = db.get(TenantSettings, tenant_id)
    if tenant_settings is not None:
        return tenant_settings

    tenant_settings = TenantSettings(
        tenant_id=tenant_id,
        allowed_kb_file_extensions=sorted(settings.supported_extensions),
        max_upload_size_mb=settings.max_upload_size_mb,
        max_chat_attachment_size_mb=settings.max_chat_attachment_size_mb,
        rag_top_k=settings.rag_top_k,
        rag_temperature=settings.rag_temperature,
        audit_log_enabled=True,
        security_scan_enabled=settings.security_scan_enabled,
    )
    db.add(tenant_settings)
    db.commit()
    db.refresh(tenant_settings)
    return tenant_settings


def update_tenant_settings(db: Session, *, tenant_settings: TenantSettings, values: dict) -> TenantSettings:
    for key, value in values.items():
        setattr(tenant_settings, key, value)
    db.add(tenant_settings)
    db.commit()
    db.refresh(tenant_settings)
    return tenant_settings
