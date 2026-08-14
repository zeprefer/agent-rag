import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.core.rbac import PERMISSION_KNOWLEDGE_MANAGE
from app.models.user import User
from app.schemas.agent import AgentCreate, AgentList, AgentRead, AgentUpdate
from app.services.agents import AgentValidationError, create_agent, get_agent, list_agents, update_agent
from app.services.audit import record_audit_log

router = APIRouter()


@router.get("/agents", response_model=AgentList)
def read_agents(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERMISSION_KNOWLEDGE_MANAGE)),
) -> AgentList:
    items, total = list_agents(db, tenant_id=current_user.tenant_id, skip=skip, limit=limit)
    return AgentList(items=[AgentRead.model_validate(item) for item in items], total=total)


@router.post("/agents", response_model=AgentRead, status_code=status.HTTP_201_CREATED)
def create_admin_agent(
    payload: AgentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERMISSION_KNOWLEDGE_MANAGE)),
) -> AgentRead:
    try:
        agent = create_agent(db, current_user=current_user, payload=payload)
    except AgentValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    record_audit_log(
        db,
        actor=current_user,
        action="agent.create",
        resource_type="agent",
        resource_id=agent.id,
        metadata={"name": agent.name, "status": agent.status},
        request=request,
    )
    return AgentRead.model_validate(agent)


@router.get("/agents/{agent_id}", response_model=AgentRead)
def read_admin_agent(
    agent_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERMISSION_KNOWLEDGE_MANAGE)),
) -> AgentRead:
    agent = get_agent(db, tenant_id=current_user.tenant_id, agent_id=agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return AgentRead.model_validate(agent)


@router.patch("/agents/{agent_id}", response_model=AgentRead)
def update_admin_agent(
    agent_id: uuid.UUID,
    payload: AgentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERMISSION_KNOWLEDGE_MANAGE)),
) -> AgentRead:
    agent = get_agent(db, tenant_id=current_user.tenant_id, agent_id=agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    before = AgentRead.model_validate(agent).model_dump(mode="json")
    try:
        agent = update_agent(db, tenant_id=current_user.tenant_id, agent=agent, payload=payload)
    except AgentValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    after = AgentRead.model_validate(agent).model_dump(mode="json")
    record_audit_log(
        db,
        actor=current_user,
        action="agent.update",
        resource_type="agent",
        resource_id=agent.id,
        metadata={"before": before, "after": after},
        request=request,
    )
    return AgentRead.model_validate(agent)


@router.delete("/agents/{agent_id}", response_model=AgentRead)
def archive_admin_agent(
    agent_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERMISSION_KNOWLEDGE_MANAGE)),
) -> AgentRead:
    agent = get_agent(db, tenant_id=current_user.tenant_id, agent_id=agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    agent = update_agent(db, tenant_id=current_user.tenant_id, agent=agent, payload=AgentUpdate(status="archived"))
    record_audit_log(
        db,
        actor=current_user,
        action="agent.archive",
        resource_type="agent",
        resource_id=agent.id,
        metadata={"name": agent.name},
        request=request,
    )
    return AgentRead.model_validate(agent)
