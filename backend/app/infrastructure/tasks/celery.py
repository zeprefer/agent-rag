"""Celery 任务派发适配器。

延迟导入真实 Task，避免 API 模块、组合根和 Worker 之间产生循环依赖。
"""

import uuid


class CeleryIndexJobDispatcher:
    def dispatch(self, job_id: uuid.UUID) -> None:
        # Lazy import keeps Celery out of the HTTP/application dependency graph
        # until a job is actually dispatched and avoids worker import cycles.
        from app.tasks import index_document_task

        index_document_task.delay(str(job_id))
