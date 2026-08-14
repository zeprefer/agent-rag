from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.agent import AgentList, AgentRead
from app.services.agents import list_agents

router = APIRouter()


@router.get("", response_model=AgentList)
def read_available_agents(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AgentList:
    items, total = list_agents(
        db,
        tenant_id=current_user.tenant_id,
        published_only=True,
        skip=skip,
        limit=limit,
    )
    return AgentList(items=[AgentRead.model_validate(item) for item in items], total=total)
