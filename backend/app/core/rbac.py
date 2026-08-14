from collections.abc import Iterable


ROLE_ADMIN = "admin"
ROLE_MANAGER = "manager"
ROLE_USER = "user"

PERMISSION_KNOWLEDGE_MANAGE = "knowledge:manage"
PERMISSION_USERS_MANAGE = "users:manage"
PERMISSION_AUDIT_READ = "audit:read"
PERMISSION_TENANT_SETTINGS_MANAGE = "tenant_settings:manage"
PERMISSION_CHAT_USE = "chat:use"

ROLE_PERMISSIONS: dict[str, set[str]] = {
    ROLE_ADMIN: {
        PERMISSION_KNOWLEDGE_MANAGE,
        PERMISSION_USERS_MANAGE,
        PERMISSION_AUDIT_READ,
        PERMISSION_TENANT_SETTINGS_MANAGE,
        PERMISSION_CHAT_USE,
    },
    ROLE_MANAGER: {
        PERMISSION_KNOWLEDGE_MANAGE,
        PERMISSION_CHAT_USE,
    },
    ROLE_USER: {
        PERMISSION_CHAT_USE,
    },
}

ROLE_DESCRIPTIONS: dict[str, str] = {
    ROLE_ADMIN: "Full tenant administration, including users, settings, audit logs, and knowledge operations.",
    ROLE_MANAGER: "Knowledge administrator who can manage knowledge bases and documents.",
    ROLE_USER: "End user who can ask questions through the user console.",
}


def supported_roles() -> tuple[str, ...]:
    return tuple(ROLE_PERMISSIONS.keys())


def permissions_for_role(role: str) -> set[str]:
    return set(ROLE_PERMISSIONS.get(role, set()))


def has_permission(role: str, permission: str) -> bool:
    return permission in permissions_for_role(role)


def has_any_permission(role: str, permissions: Iterable[str]) -> bool:
    role_permissions = permissions_for_role(role)
    return any(permission in role_permissions for permission in permissions)
