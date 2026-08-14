from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin_audit,
    admin_agents,
    admin_documents,
    admin_indexing,
    admin_knowledge_bases,
    admin_tenant_settings,
    admin_users,
    agents,
    auth,
    chat,
    health,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(admin_knowledge_bases.router, prefix="/admin", tags=["admin-knowledge-bases"])
api_router.include_router(admin_agents.router, prefix="/admin", tags=["admin-agents"])
api_router.include_router(admin_documents.router, prefix="/admin", tags=["admin-documents"])
api_router.include_router(admin_indexing.router, prefix="/admin", tags=["admin-indexing"])
api_router.include_router(admin_users.router, prefix="/admin", tags=["admin-users"])
api_router.include_router(admin_audit.router, prefix="/admin", tags=["admin-audit"])
api_router.include_router(admin_tenant_settings.router, prefix="/admin", tags=["admin-tenant-settings"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
