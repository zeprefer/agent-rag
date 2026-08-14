import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.core.rbac import PERMISSION_AUDIT_READ
from app.models.user import User
from app.schemas.admin import AuditLogList, AuditLogRead
from app.services.audit import list_audit_logs

router = APIRouter()


@router.get("/audit-logs", response_model=AuditLogList)
def read_audit_logs(
    action: str | None = None,
    resource_type: str | None = None,
    actor_user_id: uuid.UUID | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERMISSION_AUDIT_READ)),
) -> AuditLogList:
    logs = list_audit_logs(
        db,
        tenant_id=current_user.tenant_id,
        action=action,
        resource_type=resource_type,
        actor_user_id=actor_user_id,
        skip=skip,
        limit=limit,
    )
    return AuditLogList(items=[AuditLogRead.model_validate(item) for item in logs])
