"""Backward-compatible imports for object storage."""

from app.bootstrap import get_object_storage
from app.infrastructure.storage.s3 import S3ObjectStorage
from app.ports.storage import ObjectStorageError, StoredObject

ObjectStorage = S3ObjectStorage
object_storage = get_object_storage()

__all__ = ["ObjectStorage", "ObjectStorageError", "StoredObject", "object_storage"]
