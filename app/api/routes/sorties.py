from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.querying import apply_pagination, ilike_term
from app.core.security import get_current_user
from app.db.database import get_db
from app.db.models import RoleEnum, Sortie, SortieStatus, User
from app.schemas.sortie import SortieCancelRequest, SortieCreate, SortieResponse
from app.services.sortie_service import (
    cancel_sortie,
    close_sortie,
    create_sortie,
    get_sortie,
    list_sorties,
    mark_airborne,
    mark_landed,
    release_sortie,
)

router = APIRouter(prefix="/sorties", tags=["sorties"])


@router.post("", response_model=SortieResponse)
def post_sortie(
    payload: SortieCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SortieResponse:
    return SortieResponse.model_validate(create_sortie(db, current_user, payload))


@router.get("", response_model=list[SortieResponse])
def get_sortie_list(
    page: int = Query(default=1, ge=1, description="Page number."),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page."),
    search: str | None = Query(default=None, description="Search by sortie number or lesson type."),
    status: SortieStatus | None = Query(default=None, description="Filter by sortie status."),
    base_id: int | None = Query(default=None, description="Filter by base id."),
    aircraft_id: int | None = Query(default=None, description="Filter by aircraft id."),
    instructor_id: int | None = Query(default=None, description="Filter by instructor id."),
    cadet_id: int | None = Query(default=None, description="Filter by cadet id."),
    start_from: datetime | None = Query(default=None, description="Filter sorties scheduled on or after this timestamp."),
    start_to: datetime | None = Query(default=None, description="Filter sorties scheduled on or before this timestamp."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SortieResponse]:
    query = select(Sortie).order_by(Sortie.id)
    if current_user.role != RoleEnum.ADMIN:
        if current_user.role == RoleEnum.CADET:
            query = query.where(Sortie.cadet_id == current_user.id)
        elif current_user.role == RoleEnum.INSTRUCTOR:
            query = query.where(Sortie.instructor_id == current_user.id)
        else:
            query = query.where(Sortie.base_id == current_user.base_id)
    elif base_id is not None:
        query = query.where(Sortie.base_id == base_id)
    if search:
        term = ilike_term(search)
        query = query.where(or_(Sortie.sortie_number.ilike(term), Sortie.lesson_type.ilike(term)))
    if status is not None:
        query = query.where(Sortie.status == status)
    if aircraft_id is not None:
        query = query.where(Sortie.aircraft_id == aircraft_id)
    if instructor_id is not None:
        query = query.where(Sortie.instructor_id == instructor_id)
    if cadet_id is not None:
        query = query.where(Sortie.cadet_id == cadet_id)
    if start_from is not None:
        query = query.where(Sortie.scheduled_start >= start_from)
    if start_to is not None:
        query = query.where(Sortie.scheduled_start <= start_to)
    query = apply_pagination(query, page=page, page_size=page_size)
    return [SortieResponse.model_validate(item) for item in db.scalars(query)]


@router.get("/{sortie_id}", response_model=SortieResponse)
def get_sortie_item(
    sortie_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SortieResponse:
    return SortieResponse.model_validate(get_sortie(db, current_user, sortie_id))


@router.patch("/{sortie_id}/release", response_model=SortieResponse)
def patch_release_sortie(
    sortie_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SortieResponse:
    return SortieResponse.model_validate(release_sortie(db, current_user, sortie_id))


@router.patch("/{sortie_id}/airborne", response_model=SortieResponse)
def patch_airborne_sortie(
    sortie_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SortieResponse:
    return SortieResponse.model_validate(mark_airborne(db, current_user, sortie_id))


@router.patch("/{sortie_id}/landed", response_model=SortieResponse)
def patch_landed_sortie(
    sortie_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SortieResponse:
    return SortieResponse.model_validate(mark_landed(db, current_user, sortie_id))


@router.patch("/{sortie_id}/cancel", response_model=SortieResponse)
def patch_cancel_sortie(
    sortie_id: int,
    payload: SortieCancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SortieResponse:
    return SortieResponse.model_validate(cancel_sortie(db, current_user, sortie_id, payload))


@router.patch("/{sortie_id}/close", response_model=SortieResponse)
def patch_close_sortie(
    sortie_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SortieResponse:
    return SortieResponse.model_validate(close_sortie(db, current_user, sortie_id))
