import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.core.rbac import PERMISSION_USERS_MANAGE, supported_roles
from app.models.user import User
from app.schemas.admin import RoleList, UserCreate, UserList, UserUpdate
from app.schemas.user import UserRead
from app.services.audit import record_audit_log
from app.services.users import create_tenant_user, get_user, list_users, update_user

router = APIRouter()


@router.get("/roles", response_model=RoleList)
def read_roles(_: User = Depends(require_permission(PERMISSION_USERS_MANAGE))) -> RoleList:
    return RoleList.from_rbac()


@router.get("/users", response_model=UserList)
def read_users(
    role: str | None = None,
    user_status: str | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERMISSION_USERS_MANAGE)),
) -> UserList:
    items, total = list_users(
        db,
        tenant_id=current_user.tenant_id,
        role=role,
        status=user_status,
        skip=skip,
        limit=limit,
    )
    return UserList(items=[UserRead.model_validate(item) for item in items], total=total)


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_admin_user(
    payload: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERMISSION_USERS_MANAGE)),
) -> UserRead:
    if payload.role not in supported_roles():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported role")
    try:
        user = create_tenant_user(
            db,
            tenant_id=current_user.tenant_id,
            email=payload.email,
            password=payload.password,
            name=payload.name,
            role=payload.role,
            status=payload.status,
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User email already exists") from None

    record_audit_log(
        db,
        actor=current_user,
        action="user.create",
        resource_type="user",
        resource_id=user.id,
        metadata={"email": user.email, "role": user.role, "status": user.status},
        request=request,
    )
    return UserRead.model_validate(user)


@router.patch("/users/{user_id}", response_model=UserRead)
def update_admin_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERMISSION_USERS_MANAGE)),
) -> UserRead:
    target_user = get_user(db, tenant_id=current_user.tenant_id, user_id=user_id)
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if payload.role is not None and payload.role not in supported_roles():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported role")
    if target_user.id == current_user.id and payload.status == "disabled":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot disable your own account")

    before = {"name": target_user.name, "role": target_user.role, "status": target_user.status}
    updated = update_user(
        db,
        user=target_user,
        name=payload.name,
        role=payload.role,
        status=payload.status,
        password=payload.password,
    )
    after = {"name": updated.name, "role": updated.role, "status": updated.status}
    record_audit_log(
        db,
        actor=current_user,
        action="user.update",
        resource_type="user",
        resource_id=updated.id,
        metadata={"before": before, "after": after, "password_changed": payload.password is not None},
        request=request,
    )
    return UserRead.model_validate(updated)


@router.delete("/users/{user_id}", response_model=UserRead)
def disable_admin_user(
    user_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERMISSION_USERS_MANAGE)),
) -> UserRead:
    target_user = get_user(db, tenant_id=current_user.tenant_id, user_id=user_id)
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if target_user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot disable your own account")

    updated = update_user(db, user=target_user, status="disabled")
    record_audit_log(
        db,
        actor=current_user,
        action="user.disable",
        resource_type="user",
        resource_id=updated.id,
        metadata={"email": updated.email},
        request=request,
    )
    return UserRead.model_validate(updated)
