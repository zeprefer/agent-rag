"""Agent 运行策略解析服务。

统一解析 Agent、默认知识库、用户覆盖范围和运行参数，避免会话创建与问答编排
各自实现一套权限判断。
"""

import uuid
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.agent import Agent
from app.models.chat import ChatSession
from app.models.knowledge_base import KnowledgeBase
from app.services.agents import DEFAULT_AGENT_SYSTEM_PROMPT, get_agent


class KnowledgeBaseAccessError(RuntimeError):
    pass


class AgentRuntimeConfig(TypedDict):
    id: str | None
    name: str
    system_prompt: str
    chat_model: str
    temperature: float
    top_k: int
    max_context_tokens: int
    max_iterations: int
    memory_window: int
    enabled_tools: list[str]
    require_citations: bool


def resolve_knowledge_base_ids(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    requested_ids: list[uuid.UUID] | None,
) -> list[uuid.UUID]:
    filters = [KnowledgeBase.tenant_id == tenant_id, KnowledgeBase.status != "archived"]
    if requested_ids:
        filters.append(KnowledgeBase.id.in_(requested_ids))
    resolved = [row[0] for row in db.execute(select(KnowledgeBase.id).where(*filters)).all()]
    if requested_ids and len(set(resolved)) != len(set(requested_ids)):
        raise KnowledgeBaseAccessError("One or more knowledge bases are not accessible")
    return resolved


def resolve_agent(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    agent_id: uuid.UUID | None,
) -> Agent | None:
    if agent_id is None:
        return None
    agent = get_agent(db, tenant_id=tenant_id, agent_id=agent_id, published_only=True)
    if agent is None:
        raise KnowledgeBaseAccessError("Agent is not accessible")
    return agent


def effective_knowledge_base_ids(
    *,
    session: ChatSession,
    agent: Agent | None,
    override_ids: list[uuid.UUID] | None,
) -> list[uuid.UUID] | None:
    if override_ids is not None:
        return override_ids
    if session.knowledge_base_ids:
        return [uuid.UUID(item) for item in session.knowledge_base_ids]
    if agent is not None and agent.default_knowledge_base_ids:
        return [uuid.UUID(item) for item in agent.default_knowledge_base_ids]
    return None


def build_agent_config(agent: Agent | None) -> AgentRuntimeConfig:
    if agent is None:
        return {
            "id": None,
            "name": "Default enterprise assistant",
            "system_prompt": DEFAULT_AGENT_SYSTEM_PROMPT,
            "chat_model": settings.bailian_chat_model,
            "temperature": settings.rag_temperature,
            "top_k": settings.rag_top_k,
            "max_context_tokens": settings.rag_max_context_tokens,
            "max_iterations": settings.agent_max_iterations,
            "memory_window": settings.agent_memory_window,
            "enabled_tools": ["knowledge_search"],
            "require_citations": settings.agent_require_citations,
        }
    return {
        "id": str(agent.id),
        "name": agent.name,
        "system_prompt": agent.system_prompt,
        "chat_model": agent.chat_model or settings.bailian_chat_model,
        "temperature": agent.temperature,
        "top_k": agent.top_k,
        "max_context_tokens": agent.max_context_tokens,
        "max_iterations": agent.max_iterations,
        "memory_window": agent.memory_window,
        "enabled_tools": list(agent.enabled_tools or []),
        "require_citations": agent.require_citations,
    }


def build_agent_metadata(agent: Agent | None, config: AgentRuntimeConfig) -> dict:
    return {
        "id": str(agent.id) if agent is not None else None,
        "name": config["name"],
        "chat_model": config["chat_model"],
        "temperature": config["temperature"],
        "top_k": config["top_k"],
        "max_context_tokens": config["max_context_tokens"],
        "max_iterations": config["max_iterations"],
        "memory_window": config["memory_window"],
        "enabled_tools": config["enabled_tools"],
        "require_citations": config["require_citations"],
    }
