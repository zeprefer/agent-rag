"""应用组合根。

本文件集中决定“端口由哪个基础设施适配器实现”。FastAPI 路由和 Celery
任务只从这里获取依赖，因此切换模型厂商、对象存储或任务队列时，不需要修改
业务服务。缓存用于复用无状态客户端，``reset_container`` 供隔离测试清空实例。
"""

from functools import lru_cache

from app.infrastructure.ai.bailian import BailianChatProvider, BailianEmbeddingProvider, BailianVisionProvider
from app.infrastructure.storage.s3 import S3ObjectStorage
from app.infrastructure.tasks.celery import CeleryIndexJobDispatcher
from app.ports.ai import ChatProvider, EmbeddingProvider, VisionProvider
from app.ports.storage import ObjectStoragePort
from app.ports.tasks import IndexJobDispatcher


@lru_cache
def get_chat_provider() -> ChatProvider:
    return BailianChatProvider()


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    return BailianEmbeddingProvider()


@lru_cache
def get_vision_provider() -> VisionProvider:
    return BailianVisionProvider()


@lru_cache
def get_object_storage() -> ObjectStoragePort:
    return S3ObjectStorage()


@lru_cache
def get_index_job_dispatcher() -> IndexJobDispatcher:
    return CeleryIndexJobDispatcher()


def reset_container() -> None:
    """Clear adapter singletons, primarily for isolated tests."""
    get_chat_provider.cache_clear()
    get_embedding_provider.cache_clear()
    get_vision_provider.cache_clear()
    get_object_storage.cache_clear()
    get_index_job_dispatcher.cache_clear()
