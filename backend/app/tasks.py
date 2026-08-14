"""Celery Worker 任务入口。

任务入口负责创建独立数据库会话并从组合根取得存储、Embedding 适配器，实际
索引流程交给 ``indexing_commands.process_index_job``。
"""

import logging
import uuid

from app.bootstrap import get_embedding_provider, get_object_storage
from app.db.session import SessionLocal
from app.services.indexing_commands import process_index_job
from app.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="documents.index", autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 2})
def index_document_task(job_id: str) -> str:
    db = SessionLocal()
    try:
        job = process_index_job(
            db,
            job_id=uuid.UUID(job_id),
            storage=get_object_storage(),
            embedding_provider=get_embedding_provider(),
        )
        logger.info("index job processed", extra={"job_id": str(job.id), "status": job.status})
        return str(job.id)
    finally:
        db.close()
