import uuid

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.user import User


def record_audit_log(
    db: Session,
    *,
    actor: User,
    action: str,
    resource_type: str,
    resource_id: uuid.UUID | None = None,
    outcome: str = "success",
    metadata: dict | None = None,
    request: Request | None = None,
) -> AuditLog:
    log = AuditLog(
        tenant_id=actor.tenant_id,
        actor_user_id=actor.id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        outcome=outcome,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent")[:512] if request is not None and request.headers.get("user-agent") else None,
        request_id=request.headers.get("x-request-id") if request is not None else None,
        extra_metadata=metadata,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def list_audit_logs(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    action: str | None = None,
    resource_type: str | None = None,
    actor_user_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[AuditLog]:
    filters = [AuditLog.tenant_id == tenant_id]
    if action:
        filters.append(AuditLog.action == action)
    if resource_type:
        filters.append(AuditLog.resource_type == resource_type)
    if actor_user_id:
        filters.append(AuditLog.actor_user_id == actor_user_id)

    statement = (
        select(AuditLog)
        .where(*filters)
        .order_by(AuditLog.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.execute(statement).scalars().all())


def _client_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()[:64]
    if request.client is None:
        return None
    return request.client.host[:64]
