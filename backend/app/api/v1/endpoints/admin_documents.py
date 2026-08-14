import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.bootstrap import get_object_storage
from app.core.rbac import PERMISSION_KNOWLEDGE_MANAGE
from app.models.user import User
from app.ports.storage import ObjectStorageError, ObjectStoragePort
from app.schemas.document import DocumentList, DocumentRead
from app.services.audit import record_audit_log
from app.services.documents import (
    DocumentValidationError,
    create_document_from_upload,
    get_document,
    list_documents,
)
from app.services.knowledge_bases import get_knowledge_base
from app.services.security_scan import SecurityScanError
from app.services.tenant_settings import get_or_create_tenant_settings

router = APIRouter()


def _parse_tags(raw_tags: str | None) -> list[str] | None:
    if raw_tags is None:
        return None
    tags = [tag.strip() for tag in raw_tags.split(",") if tag.strip()]
    return tags or None


@router.get("/knowledge-bases/{kb_id}/documents", response_model=DocumentList)
def read_documents(
    kb_id: uuid.UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERMISSION_KNOWLEDGE_MANAGE)),
) -> DocumentList:
    knowledge_base = get_knowledge_base(db, tenant_id=current_user.tenant_id, kb_id=kb_id)
    if knowledge_base is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")

    items, total = list_documents(
        db,
        tenant_id=current_user.tenant_id,
        knowledge_base_id=knowledge_base.id,
        skip=skip,
        limit=limit,
    )
    return DocumentList(items=[DocumentRead.model_validate(item) for item in items], total=total)


@router.post(
    "/knowledge-bases/{kb_id}/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    kb_id: uuid.UUID,
    request: Request,
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    tags: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERMISSION_KNOWLEDGE_MANAGE)),
    storage: ObjectStoragePort = Depends(get_object_storage),
) -> DocumentRead:
    knowledge_base = get_knowledge_base(db, tenant_id=current_user.tenant_id, kb_id=kb_id)
    if knowledge_base is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")

    try:
        tenant_settings = get_or_create_tenant_settings(db, tenant_id=current_user.tenant_id)
        document = await create_document_from_upload(
            db,
            current_user=current_user,
            knowledge_base=knowledge_base,
            file=file,
            title=title,
            tags=_parse_tags(tags),
            tenant_settings=tenant_settings,
            storage=storage,
        )
    except DocumentValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SecurityScanError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except ObjectStorageError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    record_audit_log(
        db,
        actor=current_user,
        action="document.upload",
        resource_type="document",
        resource_id=document.id,
        metadata={
            "knowledge_base_id": str(knowledge_base.id),
            "title": document.title,
            "file_type": document.file_type,
        },
        request=request,
    )
    return DocumentRead.model_validate(document)


@router.get("/documents/{document_id}", response_model=DocumentRead)
def read_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERMISSION_KNOWLEDGE_MANAGE)),
) -> DocumentRead:
    document = get_document(db, tenant_id=current_user.tenant_id, document_id=document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return DocumentRead.model_validate(document)
