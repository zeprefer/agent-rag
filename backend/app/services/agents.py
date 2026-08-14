import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.agent import Agent
from app.models.knowledge_base import KnowledgeBase
from app.models.user import User
from app.schemas.agent import AgentCreate, AgentUpdate


DEFAULT_AGENT_SYSTEM_PROMPT = (
    "You are an enterprise knowledge agent. Answer in the user's language. "
    "Use the available knowledge tools autonomously whenever the request depends on enterprise facts. "
    "You may refine a query and search more than once before answering. "
    "Treat current user attachments as temporary context, not verified enterprise truth. "
    "If evidence is insufficient, say what cannot be confirmed and never invent facts or citations. "
    "When using enterprise evidence, mention the source document and page or section when available."
)


class AgentValidationError(ValueError):
    pass


def list_agents(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    include_archived: bool = False,
    published_only: bool = False,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[Agent], int]:
    filters = [Agent.tenant_id == tenant_id]
    if not include_archived:
        filters.append(Agent.status != "archived")
    if published_only:
        filters.append(Agent.status == "published")
    total = db.execute(select(func.count()).select_from(Agent).where(*filters)).scalar_one()
    statement = (
        select(Agent)
        .where(*filters)
        .order_by(Agent.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.execute(statement).scalars().all()), total


def get_agent(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    agent_id: uuid.UUID,
    published_only: bool = False,
) -> Agent | None:
    filters = [Agent.id == agent_id, Agent.tenant_id == tenant_id, Agent.status != "archived"]
    if published_only:
        filters.append(Agent.status == "published")
    statement = select(Agent).where(*filters)
    return db.execute(statement).scalar_one_or_none()


def create_agent(db: Session, *, current_user: User, payload: AgentCreate) -> Agent:
    kb_ids = _validate_knowledge_base_ids(
        db,
        tenant_id=current_user.tenant_id,
        knowledge_base_ids=payload.default_knowledge_base_ids,
    )
    agent = Agent(
        tenant_id=current_user.tenant_id,
        name=payload.name.strip(),
        description=payload.description,
        status=payload.status,
        system_prompt=payload.system_prompt.strip(),
        default_knowledge_base_ids=[str(item) for item in kb_ids] if kb_ids else None,
        chat_model=payload.chat_model.strip() if payload.chat_model else None,
        temperature=payload.temperature,
        top_k=payload.top_k,
        max_context_tokens=payload.max_context_tokens,
        max_iterations=payload.max_iterations,
        memory_window=payload.memory_window,
        enabled_tools=payload.enabled_tools,
        require_citations=payload.require_citations,
        created_by=current_user.id,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def update_agent(db: Session, *, tenant_id: uuid.UUID, agent: Agent, payload: AgentUpdate) -> Agent:
    values = payload.model_dump(exclude_unset=True)
    if "name" in values and values["name"] is not None:
        values["name"] = values["name"].strip()
    if "system_prompt" in values and values["system_prompt"] is not None:
        values["system_prompt"] = values["system_prompt"].strip()
    if "chat_model" in values and values["chat_model"]:
        values["chat_model"] = values["chat_model"].strip()
    if "default_knowledge_base_ids" in values:
        kb_ids = _validate_knowledge_base_ids(
            db,
            tenant_id=tenant_id,
            knowledge_base_ids=values["default_knowledge_base_ids"],
        )
        values["default_knowledge_base_ids"] = [str(item) for item in kb_ids] if kb_ids else None

    for key, value in values.items():
        setattr(agent, key, value)
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def default_agent_config() -> dict:
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
        "default_knowledge_base_ids": None,
    }


def _validate_knowledge_base_ids(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    knowledge_base_ids: list[uuid.UUID] | None,
) -> list[uuid.UUID]:
    if not knowledge_base_ids:
        return []
    statement = select(KnowledgeBase.id).where(
        KnowledgeBase.tenant_id == tenant_id,
        KnowledgeBase.status != "archived",
        KnowledgeBase.id.in_(knowledge_base_ids),
    )
    resolved = [row[0] for row in db.execute(statement).all()]
    if len(set(resolved)) != len(set(knowledge_base_ids)):
        raise AgentValidationError("One or more default knowledge bases are not accessible")
    return resolved
