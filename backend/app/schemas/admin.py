import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.rbac import ROLE_DESCRIPTIONS, ROLE_PERMISSIONS
from app.schemas.user import UserRead

UserRole = Literal["admin", "manager", "user"]
UserStatus = Literal["active", "disabled"]


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str | None = Field(default=None, max_length=120)
    role: UserRole = "user"
    status: UserStatus = "active"


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    role: UserRole | None = None
    status: UserStatus | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserList(BaseModel):
    items: list[UserRead]
    total: int


class RoleRead(BaseModel):
    role: str
    description: str
    permissions: list[str]


class RoleList(BaseModel):
    items: list[RoleRead]

    @classmethod
    def from_rbac(cls) -> "RoleList":
        return cls(
            items=[
                RoleRead(
                    role=role,
                    description=ROLE_DESCRIPTIONS[role],
                    permissions=sorted(permissions),
                )
                for role, permissions in ROLE_PERMISSIONS.items()
            ]
        )


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    actor_user_id: uuid.UUID | None
    action: str
    resource_type: str
    resource_id: uuid.UUID | None
    outcome: str
    ip_address: str | None
    user_agent: str | None
    request_id: str | None
    extra_metadata: dict | None
    created_at: datetime


class AuditLogList(BaseModel):
    items: list[AuditLogRead]


class TenantSettingsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tenant_id: uuid.UUID
    default_language: str
    allowed_kb_file_extensions: list[str]
    max_upload_size_mb: int
    max_chat_attachment_size_mb: int
    rag_top_k: int
    rag_temperature: float
    audit_log_enabled: bool
    security_scan_enabled: bool
    data_retention_days: int
    extra_metadata: dict | None
    created_at: datetime
    updated_at: datetime


class TenantSettingsUpdate(BaseModel):
    default_language: str | None = Field(default=None, min_length=2, max_length=16)
    allowed_kb_file_extensions: list[str] | None = None
    max_upload_size_mb: int | None = Field(default=None, ge=1, le=500)
    max_chat_attachment_size_mb: int | None = Field(default=None, ge=1, le=100)
    rag_top_k: int | None = Field(default=None, ge=1, le=30)
    rag_temperature: float | None = Field(default=None, ge=0, le=2)
    audit_log_enabled: bool | None = None
    security_scan_enabled: bool | None = None
    data_retention_days: int | None = Field(default=None, ge=1, le=3650)
    extra_metadata: dict | None = None
