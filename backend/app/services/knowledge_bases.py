import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.knowledge_base import KnowledgeBase
from app.models.user import User
from app.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseUpdate


def list_knowledge_bases(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[KnowledgeBase], int]:
    filters = [KnowledgeBase.tenant_id == tenant_id, KnowledgeBase.status != "archived"]
    total = db.execute(select(func.count()).select_from(KnowledgeBase).where(*filters)).scalar_one()
    statement = (
        select(KnowledgeBase)
        .where(*filters)
        .order_by(KnowledgeBase.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.execute(statement).scalars().all()), total


def get_knowledge_base(db: Session, *, tenant_id: uuid.UUID, kb_id: uuid.UUID) -> KnowledgeBase | None:
    statement = select(KnowledgeBase).where(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.tenant_id == tenant_id,
        KnowledgeBase.status != "archived",
    )
    return db.execute(statement).scalar_one_or_none()


def create_knowledge_base(db: Session, *, current_user: User, payload: KnowledgeBaseCreate) -> KnowledgeBase:
    knowledge_base = KnowledgeBase(
        tenant_id=current_user.tenant_id,
        name=payload.name.strip(),
        description=payload.description,
        visibility=payload.visibility,
        created_by=current_user.id,
    )
    db.add(knowledge_base)
    db.commit()
    db.refresh(knowledge_base)
    return knowledge_base


def update_knowledge_base(
    db: Session,
    *,
    knowledge_base: KnowledgeBase,
    payload: KnowledgeBaseUpdate,
) -> KnowledgeBase:
    update_data = payload.model_dump(exclude_unset=True)
    if "name" in update_data and update_data["name"] is not None:
        update_data["name"] = update_data["name"].strip()

    for key, value in update_data.items():
        setattr(knowledge_base, key, value)

    db.add(knowledge_base)
    db.commit()
    db.refresh(knowledge_base)
    return knowledge_base


def archive_knowledge_base(db: Session, *, knowledge_base: KnowledgeBase) -> KnowledgeBase:
    knowledge_base.status = "archived"
    db.add(knowledge_base)
    db.commit()
    db.refresh(knowledge_base)
    return knowledge_base

