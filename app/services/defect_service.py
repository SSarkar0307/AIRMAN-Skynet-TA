from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import conflict, forbidden, invalid_state, not_found
from app.core.permissions import can_manage_defect, require_role
from app.db.models import (
    Aircraft,
    AircraftStatus,
    Defect,
    DefectSeverity,
    DefectStatus,
    RoleEnum,
    Sortie,
    SortieStatus,
    User,
)
from app.schemas.defect import DefectCreate, DefectDeferRequest, DefectResolveRequest
from app.services.audit_service import write_audit_log


def list_defects(session: Session, actor: User) -> list[Defect]:
    query = select(Defect).order_by(Defect.id)
    if actor.role != RoleEnum.ADMIN:
        query = query.where(Defect.base_id == actor.base_id)
    return list(session.scalars(query))


def get_defect(session: Session, actor: User, defect_id: int) -> Defect:
    defect = session.get(Defect, defect_id)
    if defect is None:
        raise not_found("Defect not found")
    if actor.role != RoleEnum.ADMIN and defect.base_id != actor.base_id:
        raise forbidden()
    return defect


def create_defect(session: Session, actor: User, payload: DefectCreate) -> Defect:
    require_role(actor, [RoleEnum.DISPATCHER, RoleEnum.INSTRUCTOR, RoleEnum.MAINTENANCE_OFFICER])
    aircraft = session.get(Aircraft, payload.aircraft_id)
    if aircraft is None:
        raise not_found("Aircraft not found")
    if actor.role != RoleEnum.ADMIN and aircraft.base_id != actor.base_id:
        raise forbidden()
    sortie = session.get(Sortie, payload.sortie_id) if payload.sortie_id is not None else None
    if payload.sortie_id is not None and sortie is None:
        raise not_found("Sortie not found")
    if sortie is not None and sortie.base_id != aircraft.base_id:
        raise conflict("Sortie and aircraft must belong to the same base")
    defect = Defect(
        aircraft_id=aircraft.id,
        sortie_id=payload.sortie_id,
        reported_by=actor.id,
        base_id=aircraft.base_id,
        severity=payload.severity,
        description=payload.description,
        status=DefectStatus.OPEN,
    )
    session.add(defect)
    if payload.severity in {DefectSeverity.HIGH, DefectSeverity.CRITICAL}:
        aircraft.status = AircraftStatus.GROUNDED
        if defect.sortie_id is not None:
            linked_sortie = defect.sortie
            if linked_sortie is not None and linked_sortie.status in {
                SortieStatus.LANDED,
                SortieStatus.TRAINING_SUBMITTED,
                SortieStatus.TRAINING_APPROVED,
            }:
                linked_sortie.status = SortieStatus.AIRCRAFT_GROUNDED
    session.flush()
    write_audit_log(
        session,
        actor=actor,
        action="DEFECT_CREATED",
        entity_type="defect",
        entity_id=defect.id,
        new_value={"severity": defect.severity.value, "status": defect.status.value},
    )
    session.commit()
    session.refresh(defect)
    return defect


def _apply_recovery_state(session: Session, defect: Defect) -> None:
    aircraft = defect.aircraft
    open_severe = any(
        item.status == DefectStatus.OPEN and item.severity in {DefectSeverity.HIGH, DefectSeverity.CRITICAL}
        for item in aircraft.defects
    )
    if not open_severe:
        aircraft.status = AircraftStatus.READY
        if defect.sortie is not None and defect.sortie.status == SortieStatus.AIRCRAFT_GROUNDED:
            defect.sortie.status = SortieStatus.RECOVERY_REQUIRED


def resolve_defect(session: Session, actor: User, defect_id: int, payload: DefectResolveRequest) -> Defect:
    defect = get_defect(session, actor, defect_id)
    if actor.role not in {RoleEnum.ADMIN, RoleEnum.MAINTENANCE_OFFICER}:
        raise forbidden()
    if defect.status != DefectStatus.OPEN:
        raise invalid_state(f"Cannot move defect from {defect.status.value} to RESOLVED")
    old_value = {"status": defect.status.value}
    defect.status = DefectStatus.RESOLVED
    defect.resolved_by = actor.id
    defect.resolved_at = datetime.now(timezone.utc)
    defect.resolution_note = payload.resolution_note
    _apply_recovery_state(session, defect)
    session.flush()
    write_audit_log(
        session,
        actor=actor,
        action="DEFECT_RESOLVED",
        entity_type="defect",
        entity_id=defect.id,
        old_value=old_value,
        new_value={"status": defect.status.value},
        reason=payload.resolution_note,
    )
    session.commit()
    session.refresh(defect)
    return defect


def defer_defect(session: Session, actor: User, defect_id: int, payload: DefectDeferRequest) -> Defect:
    defect = get_defect(session, actor, defect_id)
    if actor.role not in {RoleEnum.ADMIN, RoleEnum.MAINTENANCE_OFFICER}:
        raise forbidden()
    if defect.status != DefectStatus.OPEN:
        raise invalid_state(f"Cannot move defect from {defect.status.value} to DEFERRED")
    old_value = {"status": defect.status.value}
    defect.status = DefectStatus.DEFERRED
    defect.resolved_by = actor.id
    defect.resolved_at = datetime.now(timezone.utc)
    defect.resolution_note = payload.resolution_note
    _apply_recovery_state(session, defect)
    session.flush()
    write_audit_log(
        session,
        actor=actor,
        action="DEFECT_DEFERRED",
        entity_type="defect",
        entity_id=defect.id,
        old_value=old_value,
        new_value={"status": defect.status.value},
        reason=payload.resolution_note,
    )
    session.commit()
    session.refresh(defect)
    return defect
