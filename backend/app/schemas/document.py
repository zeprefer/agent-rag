import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    version_no: int
    object_key: str
    original_filename: str
    content_type: str | None
    file_size: int
    file_hash: str
    parse_status: str
    parse_error: str | None
    created_at: datetime


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    knowledge_base_id: uuid.UUID
    title: str
    file_type: str
    status: str
    current_version_id: uuid.UUID | None
    created_by: uuid.UUID
    tags: dict | None
    created_at: datetime
    updated_at: datetime
    versions: list[DocumentVersionRead] = Field(default_factory=list)


class DocumentList(BaseModel):
    items: list[DocumentRead]
    total: int
