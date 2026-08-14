"""后台任务派发端口。

HTTP 层只负责提交索引任务 ID，不直接依赖 Celery，因此可以替换为 RQ、
云消息队列或同步测试实现。
"""

import uuid
from typing import Protocol


class IndexJobDispatcher(Protocol):
    """文档索引任务派发接口。"""
    def dispatch(self, job_id: uuid.UUID) -> None: ...
