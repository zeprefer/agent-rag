"""S3 兼容对象存储适配器。

封装 boto3 和存储桶管理细节，对上层只暴露 ``ObjectStoragePort`` 约定的
字节操作。当前可连接 MinIO，也可以连接兼容 S3 协议的云存储。
"""

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import Settings, settings
from app.ports.storage import ObjectStorageError, StoredObject


class S3ObjectStorage:
    """基于 boto3 的对象存储端口实现。"""
    def __init__(self, config: Settings | None = None) -> None:
        config = config or settings
        client_config = Config(s3={"addressing_style": "path" if config.s3_force_path_style else "auto"})
        self.client = boto3.client(
            "s3",
            endpoint_url=config.s3_endpoint_url,
            aws_access_key_id=config.s3_access_key_id,
            aws_secret_access_key=config.s3_secret_access_key,
            region_name=config.s3_region,
            config=client_config,
        )
        self.bucket = config.s3_bucket_name

    def ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            if error_code not in {"404", "NoSuchBucket", "NotFound"}:
                raise ObjectStorageError(f"Cannot access bucket {self.bucket}: {exc}") from exc
            try:
                self.client.create_bucket(Bucket=self.bucket)
            except ClientError as create_exc:
                raise ObjectStorageError(f"Cannot create bucket {self.bucket}: {create_exc}") from create_exc

    def put_bytes(
        self,
        *,
        object_key: str,
        data: bytes,
        content_type: str | None,
        metadata: dict[str, str] | None = None,
    ) -> StoredObject:
        self.ensure_bucket()
        try:
            response = self.client.put_object(
                Bucket=self.bucket,
                Key=object_key,
                Body=data,
                ContentType=content_type or "application/octet-stream",
                Metadata=metadata or {},
            )
        except ClientError as exc:
            raise ObjectStorageError(f"Cannot upload object {object_key}: {exc}") from exc
        return StoredObject(bucket=self.bucket, object_key=object_key, etag=response.get("ETag"))

    def get_bytes(self, *, object_key: str) -> bytes:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=object_key)
            return response["Body"].read()
        except ClientError as exc:
            raise ObjectStorageError(f"Cannot read object {object_key}: {exc}") from exc

    def delete_object(self, *, object_key: str) -> None:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=object_key)
        except ClientError as exc:
            raise ObjectStorageError(f"Cannot delete object {object_key}: {exc}") from exc
