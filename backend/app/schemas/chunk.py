import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class KnowledgeChunkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    knowledge_base_id: uuid.UUID
    document_id: uuid.UUID
    document_version_id: uuid.UUID
    chunk_index: int
    content: str
    heading_path: str | None
    page_number: int | None
    token_count: int
    extra_metadata: dict | None
    created_at: datetime

