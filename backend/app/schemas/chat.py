import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChatSessionCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    agent_id: uuid.UUID | None = None
    knowledge_base_ids: list[uuid.UUID] | None = None


class ChatSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    agent_id: uuid.UUID | None
    title: str
    status: str
    knowledge_base_ids: list[str] | None
    created_at: datetime
    updated_at: datetime


class ChatSessionList(BaseModel):
    items: list[ChatSessionRead]


class CitationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    chunk_id: uuid.UUID | None
    document_id: uuid.UUID
    document_title: str
    page_number: int | None
    heading_path: str | None
    score: float
    quote: str


class ChatMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    input_type: str
    token_count: int | None
    extra_metadata: dict | None
    citations: list[CitationRead] = Field(default_factory=list)
    created_at: datetime


class ChatMessageList(BaseModel):
    items: list[ChatMessageRead]


class ChatMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=12000)
    knowledge_base_ids: list[uuid.UUID] | None = None
    attachment_ids: list[uuid.UUID] | None = None


class ChatAnswerResponse(BaseModel):
    user_message: ChatMessageRead
    assistant_message: ChatMessageRead


class ChatAttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    session_id: uuid.UUID
    user_id: uuid.UUID
    filename: str
    content_type: str | None
    attachment_type: str
    file_size: int
    file_hash: str
    status: str
    extracted_text: str | None
    error_message: str | None
    extra_metadata: dict | None
    created_at: datetime


class ChatAttachmentList(BaseModel):
    items: list[ChatAttachmentRead]
