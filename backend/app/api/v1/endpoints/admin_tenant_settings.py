from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.core.rbac import PERMISSION_TENANT_SETTINGS_MANAGE
from app.models.user import User
from app.schemas.admin import TenantSettingsRead, TenantSettingsUpdate
from app.services.audit import record_audit_log
from app.services.tenant_settings import get_or_create_tenant_settings, update_tenant_settings

router = APIRouter()


@router.get("/tenant-settings", response_model=TenantSettingsRead)
def read_tenant_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERMISSION_TENANT_SETTINGS_MANAGE)),
) -> TenantSettingsRead:
    tenant_settings = get_or_create_tenant_settings(db, tenant_id=current_user.tenant_id)
    return TenantSettingsRead.model_validate(tenant_settings)


@router.patch("/tenant-settings", response_model=TenantSettingsRead)
def update_admin_tenant_settings(
    payload: TenantSettingsUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERMISSION_TENANT_SETTINGS_MANAGE)),
) -> TenantSettingsRead:
    tenant_settings = get_or_create_tenant_settings(db, tenant_id=current_user.tenant_id)
    values = payload.model_dump(exclude_unset=True)
    if "allowed_kb_file_extensions" in values and values["allowed_kb_file_extensions"] is not None:
        values["allowed_kb_file_extensions"] = sorted(
            {extension.lower().strip().lstrip(".") for extension in values["allowed_kb_file_extensions"] if extension.strip()}
        )
        if not values["allowed_kb_file_extensions"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one knowledge base file extension is required",
            )
    before = TenantSettingsRead.model_validate(tenant_settings).model_dump(mode="json")
    updated = update_tenant_settings(db, tenant_settings=tenant_settings, values=values)
    after = TenantSettingsRead.model_validate(updated).model_dump(mode="json")
    record_audit_log(
        db,
        actor=current_user,
        action="tenant_settings.update",
        resource_type="tenant_settings",
        resource_id=current_user.tenant_id,
        metadata={"before": before, "after": after},
        request=request,
    )
    return TenantSettingsRead.model_validate(updated)
