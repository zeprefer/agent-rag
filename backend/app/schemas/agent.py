import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    system_prompt: str = Field(min_length=20, max_length=12000)
    default_knowledge_base_ids: list[uuid.UUID] | None = None
    chat_model: str | None = Field(default=None, max_length=120)
    temperature: float = Field(default=0.2, ge=0, le=2)
    top_k: int = Field(default=8, ge=1, le=30)
    max_context_tokens: int = Field(default=3500, ge=500, le=12000)
    max_iterations: int = Field(default=4, ge=1, le=10)
    memory_window: int = Field(default=12, ge=0, le=50)
    enabled_tools: list[Literal["knowledge_search"]] = Field(default_factory=lambda: ["knowledge_search"])
    require_citations: bool = True
    status: Literal["draft", "published"] = "draft"


class AgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    system_prompt: str | None = Field(default=None, min_length=20, max_length=12000)
    default_knowledge_base_ids: list[uuid.UUID] | None = None
    chat_model: str | None = Field(default=None, max_length=120)
    temperature: float | None = Field(default=None, ge=0, le=2)
    top_k: int | None = Field(default=None, ge=1, le=30)
    max_context_tokens: int | None = Field(default=None, ge=500, le=12000)
    max_iterations: int | None = Field(default=None, ge=1, le=10)
    memory_window: int | None = Field(default=None, ge=0, le=50)
    enabled_tools: list[Literal["knowledge_search"]] | None = None
    require_citations: bool | None = None
    status: Literal["draft", "published", "archived"] | None = None


class AgentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    status: str
    system_prompt: str
    default_knowledge_base_ids: list[str] | None
    chat_model: str | None
    temperature: float
    top_k: int
    max_context_tokens: int
    max_iterations: int
    memory_window: int
    enabled_tools: list[str]
    require_citations: bool
    created_by: uuid.UUID
    extra_metadata: dict | None
    created_at: datetime
    updated_at: datetime


class AgentList(BaseModel):
    items: list[AgentRead]
    total: int
