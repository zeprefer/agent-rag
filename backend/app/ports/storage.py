"""对象存储端口。

业务层只使用字节上传、读取和删除能力，不感知底层是 MinIO、AWS S3
还是其他兼容存储。
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class StoredObject:
    bucket: str
    object_key: str
    etag: str | None = None


class ObjectStorageError(RuntimeError):
    pass


class ObjectStoragePort(Protocol):
    """文档与附件服务依赖的最小对象存储接口。"""
    def put_bytes(
        self,
        *,
        object_key: str,
        data: bytes,
        content_type: str | None,
        metadata: dict[str, str] | None = None,
    ) -> StoredObject: ...

    def get_bytes(self, *, object_key: str) -> bytes: ...

    def delete_object(self, *, object_key: str) -> None: ...
