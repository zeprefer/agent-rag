"""管理端索引 HTTP 接口。

Endpoint 通过任务派发端口提交后台任务，通过查询服务读取任务和分块，不直接
依赖 Celery，也不在接口层编写 SQL。
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.bootstrap import get_index_job_dispatcher
from app.core.rbac import PERMISSION_KNOWLEDGE_MANAGE
from app.models.user import User
from app.ports.tasks import IndexJobDispatcher
from app.schemas.chunk import KnowledgeChunkRead
from app.schemas.processing import ProcessingJobList, ProcessingJobRead
from app.services.audit import record_audit_log
from app.services.indexing_commands import IndexingError, create_index_job, fail_processing_job
from app.services.indexing_queries import list_document_chunks, list_processing_jobs

router = APIRouter()


@router.post("/documents/{document_id}/index", response_model=ProcessingJobRead)
def index_admin_document(
    document_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERMISSION_KNOWLEDGE_MANAGE)),
    dispatcher: IndexJobDispatcher = Depends(get_index_job_dispatcher),
) -> ProcessingJobRead:
    try:
        job = create_index_job(db, tenant_id=current_user.tenant_id, document_id=document_id)
        try:
            dispatcher.dispatch(job.id)
        except Exception as exc:
            job = fail_processing_job(db, job=job, error=f"Could not enqueue indexing task: {exc}")
    except IndexingError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    record_audit_log(
        db,
        actor=current_user,
        action="document.index",
        resource_type="document",
        resource_id=document_id,
        metadata={"job_id": str(job.id), "job_status": job.status},
        request=request,
    )
    return ProcessingJobRead.model_validate(job)


@router.get("/index-jobs", response_model=ProcessingJobList)
def read_index_jobs(
    document_id: uuid.UUID | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERMISSION_KNOWLEDGE_MANAGE)),
) -> ProcessingJobList:
    jobs = list_processing_jobs(
        db,
        tenant_id=current_user.tenant_id,
        document_id=document_id,
        skip=skip,
        limit=limit,
    )
    return ProcessingJobList(items=[ProcessingJobRead.model_validate(job) for job in jobs])


@router.get("/documents/{document_id}/chunks", response_model=list[KnowledgeChunkRead])
def read_document_chunks(
    document_id: uuid.UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERMISSION_KNOWLEDGE_MANAGE)),
) -> list[KnowledgeChunkRead]:
    chunks = list_document_chunks(
        db,
        tenant_id=current_user.tenant_id,
        document_id=document_id,
        skip=skip,
        limit=limit,
    )
    return [KnowledgeChunkRead.model_validate(chunk) for chunk in chunks]
