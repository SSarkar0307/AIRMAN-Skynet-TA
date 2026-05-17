from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.errors import forbidden, not_found
from app.core.permissions import is_admin
from app.core.security import get_current_user
from app.core.querying import apply_pagination, ilike_term
from app.db.database import get_db
from app.db.models import AviationBase, User
from app.schemas.base import BaseResponse

router = APIRouter(prefix="/bases", tags=["bases"])


@router.get("", response_model=list[BaseResponse])
def list_bases(
    page: int = Query(default=1, ge=1, description="Page number."),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page."),
    search: str | None = Query(default=None, description="Search by base name, code, or location."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BaseResponse]:
    query = select(AviationBase).order_by(AviationBase.id)
    if not is_admin(current_user):
        query = query.where(AviationBase.id == current_user.base_id)
    if search:
        term = ilike_term(search)
        query = query.where(
            or_(AviationBase.name.ilike(term), AviationBase.code.ilike(term), AviationBase.location.ilike(term))
        )
    query = apply_pagination(query, page=page, page_size=page_size)
    return [BaseResponse.model_validate(item) for item in db.scalars(query)]


@router.get("/{base_id}", response_model=BaseResponse)
def get_base(
    base_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BaseResponse:
    base = db.get(AviationBase, base_id)
    if base is None:
        raise not_found("Base not found")
    if not is_admin(current_user) and base.id != current_user.base_id:
        raise forbidden()
    return BaseResponse.model_validate(base)
