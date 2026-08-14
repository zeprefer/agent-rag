from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.models.tenant import Tenant
from app.models.user import User


def get_user_by_email(db: Session, email: str) -> User | None:
    statement = select(User).where(func.lower(User.email) == email.lower())
    return db.execute(statement).scalar_one_or_none()


def get_user(db: Session, *, tenant_id, user_id) -> User | None:
    statement = select(User).where(User.id == user_id, User.tenant_id == tenant_id)
    return db.execute(statement).scalar_one_or_none()


def list_users(
    db: Session,
    *,
    tenant_id,
    role: str | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[User], int]:
    filters = [User.tenant_id == tenant_id]
    if role:
        filters.append(User.role == role)
    if status:
        filters.append(User.status == status)

    total = db.execute(select(func.count()).select_from(User).where(*filters)).scalar_one()
    statement = (
        select(User)
        .where(*filters)
        .order_by(User.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.execute(statement).scalars().all()), total


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email=email)
    if user is None or user.status != "active":
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_tenant(db: Session, *, name: str) -> Tenant:
    tenant = Tenant(name=name)
    db.add(tenant)
    db.flush()
    return tenant


def create_user(
    db: Session,
    *,
    tenant: Tenant,
    email: str,
    password: str,
    name: str | None = None,
    role: str = "user",
    status: str = "active",
) -> User:
    user = User(
        tenant_id=tenant.id,
        email=email.lower(),
        name=name,
        password_hash=get_password_hash(password),
        role=role,
        status=status,
    )
    db.add(user)
    db.flush()
    return user


def create_tenant_user(
    db: Session,
    *,
    tenant_id,
    email: str,
    password: str,
    name: str | None,
    role: str,
    status: str = "active",
) -> User:
    user = User(
        tenant_id=tenant_id,
        email=email.lower(),
        name=name,
        password_hash=get_password_hash(password),
        role=role,
        status=status,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(
    db: Session,
    *,
    user: User,
    name: str | None = None,
    role: str | None = None,
    status: str | None = None,
    password: str | None = None,
) -> User:
    if name is not None:
        user.name = name
    if role is not None:
        user.role = role
    if status is not None:
        user.status = status
    if password:
        user.password_hash = get_password_hash(password)

    db.add(user)
    db.commit()
    db.refresh(user)
    return user
