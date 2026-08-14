import hashlib
import re
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.document import Document, DocumentVersion
from app.models.knowledge_base import KnowledgeBase
from app.models.tenant_settings import TenantSettings
from app.models.user import User
from app.ports.storage import ObjectStoragePort
from app.services.security_scan import scan_upload


class DocumentValidationError(ValueError):
    pass


def _safe_filename(filename: str) -> str:
    name = Path(filename).name.strip()
    if not name:
        raise DocumentValidationError("Filename is required")
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)


def _file_extension(filename: str, *, allowed_extensions: set[str] | None = None) -> str:
    allowed = allowed_extensions or settings.supported_extensions
    extension = Path(filename).suffix.lower().lstrip(".")
    if extension not in allowed:
        supported = ", ".join(sorted(allowed))
        raise DocumentValidationError(f"Unsupported file type: {extension or 'unknown'}. Supported: {supported}")
    return extension


async def read_and_validate_upload(
    file: UploadFile,
    *,
    tenant_settings: TenantSettings | None = None,
) -> tuple[str, str, bytes]:
    filename = _safe_filename(file.filename or "")
    allowed_extensions = None
    max_upload_size_mb = settings.max_upload_size_mb
    if tenant_settings is not None:
        allowed_extensions = {extension.lower().strip().lstrip(".") for extension in tenant_settings.allowed_kb_file_extensions}
        max_upload_size_mb = tenant_settings.max_upload_size_mb

    file_type = _file_extension(filename, allowed_extensions=allowed_extensions)
    data = await file.read()

    if not data:
        raise DocumentValidationError("Uploaded file is empty")
    if len(data) > max_upload_size_mb * 1024 * 1024:
        raise DocumentValidationError(f"File exceeds max size of {max_upload_size_mb} MB")

    scan_upload(filename=filename, extension=file_type, data=data, content_type=file.content_type)
    return filename, file_type, data


def list_documents(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[Document], int]:
    filters = [
        Document.tenant_id == tenant_id,
        Document.knowledge_base_id == knowledge_base_id,
        Document.status != "archived",
    ]
    total = db.execute(select(func.count()).select_from(Document).where(*filters)).scalar_one()
    statement = (
        select(Document)
        .options(selectinload(Document.versions))
        .where(*filters)
        .order_by(Document.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.execute(statement).scalars().all()), total


def get_document(db: Session, *, tenant_id: uuid.UUID, document_id: uuid.UUID) -> Document | None:
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


async def create_document_from_upload(
    db: Session,
    *,
    current_user: User,
    knowledge_base: KnowledgeBase,
    file: UploadFile,
    title: str | None = None,
    tags: list[str] | None = None,
    tenant_settings: TenantSettings | None = None,
    storage: ObjectStoragePort | None = None,
) -> Document:
    storage = storage or _default_storage()
    filename, file_type, data = await read_and_validate_upload(file, tenant_settings=tenant_settings)
    file_hash = hashlib.sha256(data).hexdigest()
    document_id = uuid.uuid4()
    version_id = uuid.uuid4()
    object_key = (
        f"tenants/{current_user.tenant_id}/knowledge-bases/{knowledge_base.id}/"
        f"documents/{document_id}/versions/{version_id}/{filename}"
    )

    storage.put_bytes(
        object_key=object_key,
        data=data,
        content_type=file.content_type,
        metadata={
            "tenant-id": str(current_user.tenant_id),
            "knowledge-base-id": str(knowledge_base.id),
            "document-id": str(document_id),
            "version-id": str(version_id),
            "sha256": file_hash,
        },
    )

    normalized_title = (title or Path(filename).stem).strip() or Path(filename).stem

    document = Document(
        id=document_id,
        tenant_id=current_user.tenant_id,
        knowledge_base_id=knowledge_base.id,
        title=normalized_title,
        file_type=file_type,
        status="uploaded",
        current_version_id=version_id,
        created_by=current_user.id,
        tags={"items": tags or []} if tags else None,
    )
    version = DocumentVersion(
        id=version_id,
        document_id=document_id,
        version_no=1,
        object_key=object_key,
        original_filename=filename,
        content_type=file.content_type,
        file_size=len(data),
        file_hash=file_hash,
        parse_status="pending",
        extra_metadata={"bucket": settings.s3_bucket_name},
    )
    document.versions.append(version)

    db.add(document)
    try:
        db.commit()
    except Exception:
        db.rollback()
        storage.delete_object(object_key=object_key)
        raise

    return get_document(db, tenant_id=current_user.tenant_id, document_id=document.id) or document


def _default_storage() -> ObjectStoragePort:
    # Backward-compatible fallback. HTTP endpoints inject this explicitly.
    from app.bootstrap import get_object_storage

    return get_object_storage()
