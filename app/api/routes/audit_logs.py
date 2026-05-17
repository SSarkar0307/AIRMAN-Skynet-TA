from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import forbidden
from app.core.permissions import is_admin
from app.core.querying import apply_pagination
from app.core.security import get_current_user
from app.db.database import get_db
from app.db.models import AuditLog, User
from app.schemas.audit_log import AuditLogResponse

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get("", response_model=list[AuditLogResponse])
def get_audit_logs(
    page: int = Query(default=1, ge=1, description="Page number."),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page."),
    entity_type: str | None = Query(default=None),
    entity_id: int | None = Query(default=None),
    action: str | None = Query(default=None, description="Filter by audit action."),
    actor_id: int | None = Query(default=None, description="Filter by actor id."),
    created_from: datetime | None = Query(default=None, description="Filter records from this timestamp."),
    created_to: datetime | None = Query(default=None, description="Filter records up to this timestamp."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AuditLogResponse]:
    query = select(AuditLog).order_by(AuditLog.id.desc())
    if entity_type is not None:
        query = query.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        query = query.where(AuditLog.entity_id == entity_id)
    if action is not None:
        query = query.where(AuditLog.action == action)
    if actor_id is not None:
        query = query.where(AuditLog.actor_id == actor_id)
    if created_from is not None:
        query = query.where(AuditLog.timestamp >= created_from)
    if created_to is not None:
        query = query.where(AuditLog.timestamp <= created_to)
    if not is_admin(current_user) and entity_type is None and entity_id is None:
        raise forbidden()
    query = apply_pagination(query, page=page, page_size=page_size)
    return [AuditLogResponse.model_validate(item) for item in db.scalars(query)]
