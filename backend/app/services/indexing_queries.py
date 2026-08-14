"""索引读模型服务。

集中提供索引任务与文档分块查询，避免 API Endpoint 直接拼装 SQL，从而保持
接口层只处理 HTTP 参数和响应转换。
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.knowledge_chunk import KnowledgeChunk
from app.models.processing import DocumentProcessingJob


def list_processing_jobs(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    document_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[DocumentProcessingJob]:
    filters = [DocumentProcessingJob.tenant_id == tenant_id]
    if document_id is not None:
        filters.append(DocumentProcessingJob.document_id == document_id)
    statement = (
        select(DocumentProcessingJob)
        .where(*filters)
        .order_by(DocumentProcessingJob.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.execute(statement).scalars().all())


def list_document_chunks(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    document_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
) -> list[KnowledgeChunk]:
    statement = (
        select(KnowledgeChunk)
        .where(
            KnowledgeChunk.document_id == document_id,
            KnowledgeChunk.tenant_id == tenant_id,
        )
        .order_by(KnowledgeChunk.chunk_index)
        .offset(skip)
        .limit(limit)
    )
    return list(db.execute(statement).scalars().all())
