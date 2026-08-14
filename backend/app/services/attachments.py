import hashlib
import re
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.chat import ChatAttachment, ChatSession
from app.models.tenant_settings import TenantSettings
from app.models.user import User
from app.ports.ai import VisionProvider
from app.ports.storage import ObjectStoragePort
from app.services.chunking import estimate_token_count
from app.services.document_parsers import DocumentParseError, parse_document_bytes
from app.services.security_scan import scan_upload


class AttachmentValidationError(ValueError):
    pass


class AttachmentProcessingError(RuntimeError):
    pass


def list_attachments(
    db: Session,
    *,
    current_user: User,
    session_id: uuid.UUID,
) -> list[ChatAttachment]:
    statement = (
        select(ChatAttachment)
        .where(
            ChatAttachment.tenant_id == current_user.tenant_id,
            ChatAttachment.user_id == current_user.id,
            ChatAttachment.session_id == session_id,
        )
        .order_by(ChatAttachment.created_at.desc())
    )
    return list(db.execute(statement).scalars().all())


def delete_chat_attachments(
    db: Session,
    *,
    current_user: User,
    session_id: uuid.UUID,
    storage: ObjectStoragePort | None = None,
) -> None:
    storage = storage or _default_storage()
    attachments = list_attachments(db, current_user=current_user, session_id=session_id)
    for attachment in attachments:
        storage.delete_object(object_key=attachment.object_key)


def get_attachments_for_message(
    db: Session,
    *,
    current_user: User,
    session_id: uuid.UUID,
    attachment_ids: list[uuid.UUID] | None,
) -> list[ChatAttachment]:
    if not attachment_ids:
        return []
    statement = select(ChatAttachment).where(
        ChatAttachment.tenant_id == current_user.tenant_id,
        ChatAttachment.user_id == current_user.id,
        ChatAttachment.session_id == session_id,
        ChatAttachment.id.in_(attachment_ids),
        ChatAttachment.status == "processed",
    )
    attachments = list(db.execute(statement).scalars().all())
    if len({item.id for item in attachments}) != len(set(attachment_ids)):
        raise AttachmentValidationError("One or more attachments are not accessible or not processed")
    return attachments


async def create_chat_attachment(
    db: Session,
    *,
    current_user: User,
    session: ChatSession,
    file: UploadFile,
    tenant_settings: TenantSettings | None = None,
    storage: ObjectStoragePort | None = None,
    vision_provider: VisionProvider | None = None,
) -> ChatAttachment:
    storage = storage or _default_storage()
    filename, extension, attachment_type, data = await _read_and_validate(file, tenant_settings=tenant_settings)
    file_hash = hashlib.sha256(data).hexdigest()
    attachment_id = uuid.uuid4()
    object_key = (
        f"tenants/{current_user.tenant_id}/chat-sessions/{session.id}/"
        f"attachments/{attachment_id}/{filename}"
    )

    storage.put_bytes(
        object_key=object_key,
        data=data,
        content_type=file.content_type,
        metadata={
            "tenant-id": str(current_user.tenant_id),
            "session-id": str(session.id),
            "attachment-id": str(attachment_id),
            "sha256": file_hash,
        },
    )

    try:
        extracted_text, metadata = _extract_attachment_text(
            data=data,
            filename=filename,
            extension=extension,
            attachment_type=attachment_type,
            content_type=file.content_type,
            vision_provider=vision_provider,
        )
        status = "processed"
        error_message = None
    except Exception as exc:
        extracted_text = None
        metadata = {}
        status = "failed"
        error_message = str(exc)

    attachment = ChatAttachment(
        id=attachment_id,
        tenant_id=current_user.tenant_id,
        session_id=session.id,
        user_id=current_user.id,
        filename=filename,
        content_type=file.content_type,
        attachment_type=attachment_type,
        object_key=object_key,
        file_size=len(data),
        file_hash=file_hash,
        status=status,
        extracted_text=extracted_text,
        error_message=error_message,
        extra_metadata=metadata,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    if status == "failed":
        raise AttachmentProcessingError(error_message or "Attachment processing failed")
    return attachment


def build_attachment_context(attachments: list[ChatAttachment]) -> tuple[str, list[dict]]:
    blocks: list[str] = []
    metadata: list[dict] = []
    used_tokens = 0
    for index, attachment in enumerate(attachments, start=1):
        text = (attachment.extracted_text or "").strip()
        if not text:
            continue
        token_count = estimate_token_count(text)
        if used_tokens + token_count > settings.rag_max_context_tokens and blocks:
            break
        used_tokens += token_count
        blocks.append(
            f"[Attachment {index}]\n"
            f"Filename: {attachment.filename}\n"
            f"Type: {attachment.attachment_type}\n"
            f"Content:\n{text[:6000]}"
        )
        metadata.append(
            {
                "id": str(attachment.id),
                "filename": attachment.filename,
                "attachment_type": attachment.attachment_type,
                "token_count": token_count,
            }
        )
    return "\n\n".join(blocks), metadata


async def _read_and_validate(
    file: UploadFile,
    *,
    tenant_settings: TenantSettings | None = None,
) -> tuple[str, str, str, bytes]:
    filename = _safe_filename(file.filename or "")
    extension = Path(filename).suffix.lower().lstrip(".")
    if extension in settings.supported_chat_image_exts:
        attachment_type = "image"
    elif extension in settings.supported_chat_file_exts:
        attachment_type = "file"
    else:
        supported = sorted(settings.supported_chat_file_exts | settings.supported_chat_image_exts)
        raise AttachmentValidationError(f"Unsupported attachment type: {extension or 'unknown'}. Supported: {', '.join(supported)}")

    data = await file.read()
    if not data:
        raise AttachmentValidationError("Uploaded attachment is empty")
    max_size_mb = tenant_settings.max_chat_attachment_size_mb if tenant_settings is not None else settings.max_chat_attachment_size_mb
    if len(data) > max_size_mb * 1024 * 1024:
        raise AttachmentValidationError(f"Attachment exceeds max size of {max_size_mb} MB")
    scan_upload(filename=filename, extension=extension, data=data, content_type=file.content_type)
    return filename, extension, attachment_type, data


def _extract_attachment_text(
    *,
    data: bytes,
    filename: str,
    extension: str,
    attachment_type: str,
    content_type: str | None,
    vision_provider: VisionProvider | None,
) -> tuple[str, dict]:
    if attachment_type == "image":
        provider = vision_provider or _default_vision_provider()
        text, metadata = provider.describe_image(data=data, content_type=content_type)
        return text, {"provider": metadata}

    try:
        sections = parse_document_bytes(file_type=extension, filename=filename, data=data)
    except DocumentParseError as exc:
        raise AttachmentProcessingError(str(exc)) from exc
    text = "\n\n".join(section.text for section in sections if section.text.strip())
    if not text.strip():
        raise AttachmentProcessingError("No text extracted from attachment")
    return text, {"section_count": len(sections)}


def _safe_filename(filename: str) -> str:
    name = Path(filename).name.strip()
    if not name:
        raise AttachmentValidationError("Filename is required")
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)


def _default_storage() -> ObjectStoragePort:
    # Transitional fallback for callers of the former public function shape.
    # New composition roots pass the dependency explicitly.
    from app.bootstrap import get_object_storage

    return get_object_storage()


def _default_vision_provider() -> VisionProvider:
    from app.bootstrap import get_vision_provider

    return get_vision_provider()
