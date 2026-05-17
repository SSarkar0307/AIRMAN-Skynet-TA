from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.core.querying import apply_pagination, ilike_term
from app.db.database import get_db
from app.db.models import Aircraft, AircraftStatus, RoleEnum, User
from app.schemas.aircraft import AircraftCreate, AircraftResponse
from app.services.aircraft_service import create_aircraft, get_aircraft, ground_aircraft, mark_aircraft_ready

router = APIRouter(prefix="/aircraft", tags=["aircraft"])


@router.post("", response_model=AircraftResponse)
def post_aircraft(
    payload: AircraftCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AircraftResponse:
    return AircraftResponse.model_validate(create_aircraft(db, current_user, payload))


@router.get("", response_model=list[AircraftResponse])
def get_aircraft_list(
    page: int = Query(default=1, ge=1, description="Page number."),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page."),
    search: str | None = Query(default=None, description="Search by registration or aircraft type."),
    status: AircraftStatus | None = Query(default=None, description="Filter by aircraft status."),
    base_id: int | None = Query(default=None, description="Filter by base id."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AircraftResponse]:
    query = select(Aircraft).order_by(Aircraft.id)
    if current_user.role != RoleEnum.ADMIN:
        query = query.where(Aircraft.base_id == current_user.base_id)
    elif base_id is not None:
        query = query.where(Aircraft.base_id == base_id)
    if search:
        term = ilike_term(search)
        query = query.where(or_(Aircraft.registration.ilike(term), Aircraft.aircraft_type.ilike(term)))
    if status is not None:
        query = query.where(Aircraft.status == status)
    query = apply_pagination(query, page=page, page_size=page_size)
    return [AircraftResponse.model_validate(item) for item in db.scalars(query)]


@router.get("/{aircraft_id}", response_model=AircraftResponse)
def get_aircraft_item(
    aircraft_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AircraftResponse:
    return AircraftResponse.model_validate(get_aircraft(db, current_user, aircraft_id))


@router.patch("/{aircraft_id}/ground", response_model=AircraftResponse)
def patch_ground_aircraft(
    aircraft_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AircraftResponse:
    return AircraftResponse.model_validate(ground_aircraft(db, current_user, aircraft_id))


@router.patch("/{aircraft_id}/ready", response_model=AircraftResponse)
def patch_ready_aircraft(
    aircraft_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AircraftResponse:
    return AircraftResponse.model_validate(mark_aircraft_ready(db, current_user, aircraft_id))
