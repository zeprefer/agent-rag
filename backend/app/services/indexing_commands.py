"""文档索引命令服务。

负责索引任务状态机和写操作：读取原文件、解析、切片、向量化及持久化。
对象存储与 Embedding Provider 都显式注入，命令服务不依赖具体基础设施。
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.models.document import Document, DocumentVersion
from app.models.knowledge_chunk import ChunkEmbedding, KnowledgeChunk
from app.models.processing import DocumentProcessingJob
from app.ports.ai import AIProviderConfigError, EmbeddingProvider, EmbeddingProviderError
from app.ports.storage import ObjectStorageError, ObjectStoragePort
from app.services.chunking import TextChunk, build_chunks
from app.services.document_parsers import DocumentParseError, parse_document_bytes


class IndexingError(RuntimeError):
    pass


def create_index_job(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    document_id: uuid.UUID,
) -> DocumentProcessingJob:
    document = _get_document_for_indexing(db, tenant_id=tenant_id, document_id=document_id)
    if document is None:
        raise IndexingError("Document not found")

    version = _get_current_version(document)
    if version is None:
        raise IndexingError("Document has no current version")

    job = DocumentProcessingJob(
        tenant_id=tenant_id,
        document_id=document.id,
        document_version_id=version.id,
        job_type="index",
        status="queued",
    )
    db.add(job)
    document.status = "indexing"
    version.parse_status = "pending"
    version.parse_error = None
    db.commit()
    db.refresh(job)
    return job


def index_document(
    db: Session,
    *,
    storage: ObjectStoragePort,
    embedding_provider: EmbeddingProvider,
    tenant_id: uuid.UUID,
    document_id: uuid.UUID,
) -> DocumentProcessingJob:
    job = create_index_job(db, tenant_id=tenant_id, document_id=document_id)
    return process_index_job(
        db,
        job_id=job.id,
        storage=storage,
        embedding_provider=embedding_provider,
    )


def process_index_job(
    db: Session,
    *,
    job_id: uuid.UUID,
    storage: ObjectStoragePort,
    embedding_provider: EmbeddingProvider,
) -> DocumentProcessingJob:
    """执行一个已创建的索引任务，并将成功或失败状态可靠写回数据库。"""
    job = db.get(DocumentProcessingJob, job_id)
    if job is None:
        raise IndexingError("Processing job not found")

    document = _get_document_for_indexing(db, tenant_id=job.tenant_id, document_id=job.document_id)
    if document is None:
        raise IndexingError("Document not found")

    version = _get_current_version(document)
    if version is None or version.id != job.document_version_id:
        fail_processing_job(db, job=job, error="Document version is no longer current")
        return job

    job.status = "running"
    job.started_at = datetime.now(UTC)
    document.status = "indexing"
    version.parse_status = "processing"
    version.parse_error = None
    db.commit()
    db.refresh(job)

    try:
        data = storage.get_bytes(object_key=version.object_key)
        sections = parse_document_bytes(
            file_type=document.file_type,
            filename=version.original_filename,
            data=data,
        )
        chunks = build_chunks(sections)
        if not chunks:
            raise IndexingError("Parser produced no chunks")

        _replace_chunks_with_embeddings(
            db,
            document=document,
            version=version,
            chunks=chunks,
            embedding_provider=embedding_provider,
        )

        document.status = "indexed"
        version.parse_status = "success"
        job.status = "success"
        job.finished_at = datetime.now(UTC)
        job.chunk_count = len(chunks)
        job.extra_metadata = {
            "embedding_model": embedding_provider.model,
            "embedding_dimensions": embedding_provider.dimensions,
        }
        db.commit()
        db.refresh(job)
        return job
    except (AIProviderConfigError, DocumentParseError, EmbeddingProviderError, ObjectStorageError, IndexingError) as exc:
        _mark_failed(db, document=document, version=version, job=job, error=str(exc))
        return job
    except Exception as exc:
        _mark_failed(db, document=document, version=version, job=job, error=f"Unexpected indexing failure: {exc}")
        return job


def fail_processing_job(
    db: Session,
    *,
    job: DocumentProcessingJob,
    error: str,
) -> DocumentProcessingJob:
    document = _get_document_for_indexing(db, tenant_id=job.tenant_id, document_id=job.document_id)
    version = _get_current_version(document) if document is not None else None
    if document is not None:
        document.status = "failed"
    if version is not None:
        version.parse_status = "failed"
        version.parse_error = error[:4000]
    job.status = "failed"
    job.finished_at = datetime.now(UTC)
    job.error_message = error[:4000]
    db.commit()
    db.refresh(job)
    return job


def _get_document_for_indexing(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    document_id: uuid.UUID,
) -> Document | None:
    statement = (
        select(Document)
        .options(selectinload(Document.versions))
        .where(
            Document.id == document_id,
            Document.tenant_id == tenant_id,
            Document.status != "archived",
        )
    )
    return db.execute(statement).scalar_one_or_none()


def _get_current_version(document: Document) -> DocumentVersion | None:
    if document.current_version_id is None:
        return None
    return next(
        (version for version in document.versions if version.id == document.current_version_id),
        None,
    )


def _replace_chunks_with_embeddings(
    db: Session,
    *,
    document: Document,
    version: DocumentVersion,
    chunks: list[TextChunk],
    embedding_provider: EmbeddingProvider,
) -> None:
    """原子替换当前版本的分块和向量；批处理策略由 Provider 自己负责。"""
    db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_version_id == version.id))
    db.flush()

    chunk_rows: list[KnowledgeChunk] = []
    for index, chunk in enumerate(chunks):
        row = KnowledgeChunk(
            tenant_id=document.tenant_id,
            knowledge_base_id=document.knowledge_base_id,
            document_id=document.id,
            document_version_id=version.id,
            chunk_index=index,
            content=chunk.content,
            heading_path=chunk.heading_path,
            page_number=chunk.page_number,
            token_count=chunk.token_count,
            extra_metadata=chunk.metadata,
        )
        db.add(row)
        chunk_rows.append(row)
    db.flush()

    embeddings = embedding_provider.embed_texts([row.content for row in chunk_rows])
    if len(embeddings) != len(chunk_rows):
        raise EmbeddingProviderError(
            f"Embedding count mismatch: expected {len(chunk_rows)}, got {len(embeddings)}"
        )
    for row, embedding in zip(chunk_rows, embeddings, strict=True):
        db.add(
            ChunkEmbedding(
                chunk_id=row.id,
                embedding_model=embedding_provider.model,
                embedding=embedding,
            )
        )


def _mark_failed(
    db: Session,
    *,
    document: Document,
    version: DocumentVersion,
    job: DocumentProcessingJob,
    error: str,
) -> None:
    document.status = "failed"
    version.parse_status = "failed"
    version.parse_error = error[:4000]
    job.status = "failed"
    job.finished_at = datetime.now(UTC)
    job.error_message = error[:4000]
    db.commit()
    db.refresh(job)
