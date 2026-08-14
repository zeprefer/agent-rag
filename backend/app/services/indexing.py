"""旧版索引服务兼容门面。

新代码应分别依赖 ``indexing_commands`` 与 ``indexing_queries``；这里仅保持
历史函数签名，并通过组合根补齐存储及 Embedding 依赖。
"""

from sqlalchemy.orm import Session

from app.bootstrap import get_embedding_provider, get_object_storage
from app.services.indexing_commands import (
    IndexingError,
    create_index_job,
    fail_processing_job,
    index_document as _index_document,
    process_index_job as _process_index_job,
)
from app.services.indexing_queries import list_document_chunks, list_processing_jobs


def index_document(db: Session, **kwargs):
    return _index_document(
        db,
        storage=get_object_storage(),
        embedding_provider=get_embedding_provider(),
        **kwargs,
    )


def process_index_job(db: Session, **kwargs):
    return _process_index_job(
        db,
        storage=get_object_storage(),
        embedding_provider=get_embedding_provider(),
        **kwargs,
    )


__all__ = [
    "IndexingError",
    "create_index_job",
    "fail_processing_job",
    "index_document",
    "list_document_chunks",
    "list_processing_jobs",
    "process_index_job",
]
