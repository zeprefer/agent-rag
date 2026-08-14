import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.core.rbac import PERMISSION_KNOWLEDGE_MANAGE
from app.models.user import User
from app.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseList, KnowledgeBaseRead, KnowledgeBaseUpdate
from app.services.audit import record_audit_log
from app.services.knowledge_bases import (
    archive_knowledge_base,
    create_knowledge_base,
    get_knowledge_base,
    list_knowledge_bases,
    update_knowledge_base,
)

router = APIRouter()


@router.get("/knowledge-bases", response_model=KnowledgeBaseList)
def read_knowledge_bases(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERMISSION_KNOWLEDGE_MANAGE)),
) -> KnowledgeBaseList:
    items, total = list_knowledge_bases(db, tenant_id=current_user.tenant_id, skip=skip, limit=limit)
    return KnowledgeBaseList(items=[KnowledgeBaseRead.model_validate(item) for item in items], total=total)


@router.post("/knowledge-bases", response_model=KnowledgeBaseRead, status_code=status.HTTP_201_CREATED)
def create_admin_knowledge_base(
    payload: KnowledgeBaseCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERMISSION_KNOWLEDGE_MANAGE)),
) -> KnowledgeBaseRead:
    try:
        knowledge_base = create_knowledge_base(db, current_user=current_user, payload=payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Knowledge base with the same name already exists",
        ) from None
    record_audit_log(
        db,
        actor=current_user,
        action="knowledge_base.create",
        resource_type="knowledge_base",
        resource_id=knowledge_base.id,
        metadata={"name": knowledge_base.name, "visibility": knowledge_base.visibility},
        request=request,
    )
    return KnowledgeBaseRead.model_validate(knowledge_base)


@router.get("/knowledge-bases/{kb_id}", response_model=KnowledgeBaseRead)
def read_knowledge_base(
    kb_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERMISSION_KNOWLEDGE_MANAGE)),
) -> KnowledgeBaseRead:
    knowledge_base = get_knowledge_base(db, tenant_id=current_user.tenant_id, kb_id=kb_id)
    if knowledge_base is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")
    return KnowledgeBaseRead.model_validate(knowledge_base)


@router.patch("/knowledge-bases/{kb_id}", response_model=KnowledgeBaseRead)
def update_admin_knowledge_base(
    kb_id: uuid.UUID,
    payload: KnowledgeBaseUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERMISSION_KNOWLEDGE_MANAGE)),
) -> KnowledgeBaseRead:
    knowledge_base = get_knowledge_base(db, tenant_id=current_user.tenant_id, kb_id=kb_id)
    if knowledge_base is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")
    before = KnowledgeBaseRead.model_validate(knowledge_base).model_dump(mode="json")
    try:
        knowledge_base = update_knowledge_base(db, knowledge_base=knowledge_base, payload=payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Knowledge base with the same name already exists",
        ) from None
    after = KnowledgeBaseRead.model_validate(knowledge_base).model_dump(mode="json")
    record_audit_log(
        db,
        actor=current_user,
        action="knowledge_base.update",
        resource_type="knowledge_base",
        resource_id=knowledge_base.id,
        metadata={"before": before, "after": after},
        request=request,
    )
    return KnowledgeBaseRead.model_validate(knowledge_base)


@router.delete("/knowledge-bases/{kb_id}", response_model=KnowledgeBaseRead)
def archive_admin_knowledge_base(
    kb_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERMISSION_KNOWLEDGE_MANAGE)),
) -> KnowledgeBaseRead:
    knowledge_base = get_knowledge_base(db, tenant_id=current_user.tenant_id, kb_id=kb_id)
    if knowledge_base is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")
    knowledge_base = archive_knowledge_base(db, knowledge_base=knowledge_base)
    record_audit_log(
        db,
        actor=current_user,
        action="knowledge_base.archive",
        resource_type="knowledge_base",
        resource_id=knowledge_base.id,
        metadata={"name": knowledge_base.name},
        request=request,
    )
    return KnowledgeBaseRead.model_validate(knowledge_base)
