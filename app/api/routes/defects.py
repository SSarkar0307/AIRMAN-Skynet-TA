from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.querying import apply_pagination, ilike_term
from app.core.security import get_current_user
from app.db.database import get_db
from app.db.models import Defect, DefectSeverity, DefectStatus, RoleEnum, User
from app.schemas.defect import DefectCreate, DefectDeferRequest, DefectResponse, DefectResolveRequest
from app.services.defect_service import create_defect, defer_defect, get_defect, list_defects, resolve_defect

router = APIRouter(prefix="/defects", tags=["defects"])


@router.post("", response_model=DefectResponse)
def post_defect(
    payload: DefectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DefectResponse:
    return DefectResponse.model_validate(create_defect(db, current_user, payload))


@router.get("", response_model=list[DefectResponse])
def get_defect_list(
    page: int = Query(default=1, ge=1, description="Page number."),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page."),
    search: str | None = Query(default=None, description="Search by defect description."),
    status: DefectStatus | None = Query(default=None, description="Filter by defect status."),
    severity: DefectSeverity | None = Query(default=None, description="Filter by defect severity."),
    base_id: int | None = Query(default=None, description="Filter by base id."),
    aircraft_id: int | None = Query(default=None, description="Filter by aircraft id."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DefectResponse]:
    query = select(Defect).order_by(Defect.id)
    if current_user.role != RoleEnum.ADMIN:
        query = query.where(Defect.base_id == current_user.base_id)
    elif base_id is not None:
        query = query.where(Defect.base_id == base_id)
    if search:
        query = query.where(Defect.description.ilike(ilike_term(search)))
    if status is not None:
        query = query.where(Defect.status == status)
    if severity is not None:
        query = query.where(Defect.severity == severity)
    if aircraft_id is not None:
        query = query.where(Defect.aircraft_id == aircraft_id)
    query = apply_pagination(query, page=page, page_size=page_size)
    return [DefectResponse.model_validate(item) for item in db.scalars(query)]


@router.get("/{defect_id}", response_model=DefectResponse)
def get_defect_item(
    defect_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DefectResponse:
    return DefectResponse.model_validate(get_defect(db, current_user, defect_id))


@router.patch("/{defect_id}/resolve", response_model=DefectResponse)
def patch_resolve(
    defect_id: int,
    payload: DefectResolveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DefectResponse:
    return DefectResponse.model_validate(resolve_defect(db, current_user, defect_id, payload))


@router.patch("/{defect_id}/defer", response_model=DefectResponse)
def patch_defer(
    defect_id: int,
    payload: DefectDeferRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DefectResponse:
    return DefectResponse.model_validate(defer_defect(db, current_user, defect_id, payload))
