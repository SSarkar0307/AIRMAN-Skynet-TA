from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.errors import forbidden, not_found
from app.core.permissions import is_admin
from app.core.security import get_current_user
from app.core.querying import apply_pagination, ilike_term
from app.db.database import get_db
from app.db.models import RoleEnum, User
from app.schemas.user import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserResponse])
def list_users(
    page: int = Query(default=1, ge=1, description="Page number."),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page."),
    search: str | None = Query(default=None, description="Search by name or email."),
    role: RoleEnum | None = Query(default=None, description="Filter by role."),
    base_id: int | None = Query(default=None, description="Filter by base id."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[UserResponse]:
    query = select(User).order_by(User.id)
    if not is_admin(current_user):
        query = query.where(User.base_id == current_user.base_id)
    if search:
        term = ilike_term(search)
        query = query.where(or_(User.full_name.ilike(term), User.email.ilike(term)))
    if role:
        query = query.where(User.role == role)
    if base_id is not None and is_admin(current_user):
        query = query.where(User.base_id == base_id)
    query = apply_pagination(query, page=page, page_size=page_size)
    return [UserResponse.model_validate(user) for user in db.scalars(query)]


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    user = db.get(User, user_id)
    if user is None:
        raise not_found("User not found")
    if not is_admin(current_user) and user.base_id != current_user.base_id and user.id != current_user.id:
        raise forbidden()
    return UserResponse.model_validate(user)
