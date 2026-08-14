import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProcessingJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    document_id: uuid.UUID
    document_version_id: uuid.UUID
    job_type: str
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None
    chunk_count: int
    extra_metadata: dict | None
    created_at: datetime
    updated_at: datetime


class ProcessingJobList(BaseModel):
    items: list[ProcessingJobRead]

