from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import conflict, forbidden, invalid_state, not_found, validation_error
from app.core.permissions import can_view_sortie, require_role, require_same_base
from app.db.models import (
    Aircraft,
    AircraftStatus,
    DefectSeverity,
    DefectStatus,
    RoleEnum,
    Sortie,
    SortieStatus,
    TrainingProgress,
    TrainingStatus,
    User,
)
from app.schemas.sortie import SortieCancelRequest, SortieCreate
from app.services.aircraft_service import ensure_aircraft_assignable
from app.services.audit_service import write_audit_log


def list_sorties(session: Session, actor: User) -> list[Sortie]:
    query = select(Sortie).order_by(Sortie.id)
    if actor.role == RoleEnum.ADMIN:
        return list(session.scalars(query))
    if actor.role == RoleEnum.CADET:
        query = query.where(Sortie.cadet_id == actor.id)
    elif actor.role == RoleEnum.INSTRUCTOR:
        query = query.where(Sortie.instructor_id == actor.id)
    else:
        query = query.where(Sortie.base_id == actor.base_id)
    return list(session.scalars(query))


def get_sortie(session: Session, actor: User, sortie_id: int) -> Sortie:
    sortie = session.get(Sortie, sortie_id)
    if sortie is None:
        raise not_found("Sortie not found")
    if not can_view_sortie(actor, sortie):
        raise forbidden()
    return sortie


def create_sortie(session: Session, actor: User, payload: SortieCreate) -> Sortie:
    require_role(actor, [RoleEnum.DISPATCHER])
    if actor.role != RoleEnum.ADMIN and actor.base_id != payload.base_id:
        raise forbidden()
    if payload.scheduled_end <= payload.scheduled_start:
        raise validation_error("scheduled_end must be after scheduled_start", field="scheduled_end")
    if session.scalar(select(Sortie).where(Sortie.sortie_number == payload.sortie_number)):
        raise conflict("Sortie number already exists")
    cadet = session.get(User, payload.cadet_id)
    instructor = session.get(User, payload.instructor_id)
    aircraft = session.get(Aircraft, payload.aircraft_id)
    if cadet is None or instructor is None or aircraft is None:
        raise not_found("Referenced record not found")
    if cadet.role != RoleEnum.CADET:
        raise validation_error("cadet_id must reference a cadet", field="cadet_id")
    if instructor.role != RoleEnum.INSTRUCTOR:
        raise validation_error("instructor_id must reference an instructor", field="instructor_id")
    if aircraft.base_id != payload.base_id or cadet.base_id != payload.base_id or instructor.base_id != payload.base_id:
        raise conflict("Base mismatch between sortie participants and aircraft")
    ensure_aircraft_assignable(session, aircraft, payload.scheduled_start, payload.scheduled_end)
    sortie = Sortie(
        sortie_number=payload.sortie_number,
        cadet_id=cadet.id,
        instructor_id=instructor.id,
        aircraft_id=aircraft.id,
        base_id=payload.base_id,
        lesson_type=payload.lesson_type,
        scheduled_start=payload.scheduled_start,
        scheduled_end=payload.scheduled_end,
        status=SortieStatus.SCHEDULED,
    )
    session.add(sortie)
    aircraft.status = AircraftStatus.SCHEDULED
    session.flush()
    write_audit_log(
        session,
        actor=actor,
        action="SORTIE_CREATED",
        entity_type="sortie",
        entity_id=sortie.id,
        new_value={"sortie_number": sortie.sortie_number, "status": sortie.status.value},
    )
    session.commit()
    session.refresh(sortie)
    return sortie


def _transition_sortie(
    session: Session,
    *,
    actor: User,
    sortie: Sortie,
    allowed_from: set[SortieStatus],
    next_status: SortieStatus,
    action: str,
    reason: str | None = None,
    actual_time_field: str | None = None,
) -> Sortie:
    if sortie.status not in allowed_from:
        raise invalid_state(f"Cannot move sortie from {sortie.status.value} to {next_status.value}")
    old_value = {"status": sortie.status.value}
    sortie.status = next_status
    if actual_time_field == "actual_start" and sortie.actual_start is None:
        sortie.actual_start = datetime.now(timezone.utc)
    if actual_time_field == "actual_end" and sortie.actual_end is None:
        sortie.actual_end = datetime.now(timezone.utc)
    session.flush()
    write_audit_log(
        session,
        actor=actor,
        action=action,
        entity_type="sortie",
        entity_id=sortie.id,
        old_value=old_value,
        new_value={"status": sortie.status.value},
        reason=reason,
    )
    return sortie


def release_sortie(session: Session, actor: User, sortie_id: int) -> Sortie:
    require_role(actor, [RoleEnum.DISPATCHER])
    sortie = get_sortie(session, actor, sortie_id)
    if actor.role != RoleEnum.ADMIN and sortie.base_id != actor.base_id:
        raise forbidden()
    if sortie.status != SortieStatus.SCHEDULED:
        raise invalid_state(f"Cannot move sortie from {sortie.status.value} to RELEASED")
    if sortie.aircraft.status in {AircraftStatus.GROUNDED, AircraftStatus.MAINTENANCE}:
        raise conflict("Aircraft is grounded and cannot be released")
    ensure_aircraft_assignable(session, sortie.aircraft, sortie.scheduled_start, sortie.scheduled_end, sortie_id=sortie.id)
    sortie.aircraft.status = AircraftStatus.SCHEDULED
    _transition_sortie(
        session,
        actor=actor,
        sortie=sortie,
        allowed_from={SortieStatus.SCHEDULED},
        next_status=SortieStatus.RELEASED,
        action="SORTIE_RELEASED",
    )
    session.commit()
    session.refresh(sortie)
    return sortie


def mark_airborne(session: Session, actor: User, sortie_id: int) -> Sortie:
    require_role(actor, [RoleEnum.DISPATCHER])
    sortie = get_sortie(session, actor, sortie_id)
    if sortie.status != SortieStatus.RELEASED:
        raise invalid_state(f"Cannot move sortie from {sortie.status.value} to AIRBORNE")
    sortie.aircraft.status = AircraftStatus.AIRBORNE
    _transition_sortie(
        session,
        actor=actor,
        sortie=sortie,
        allowed_from={SortieStatus.RELEASED},
        next_status=SortieStatus.AIRBORNE,
        action="SORTIE_AIRBORNE",
        actual_time_field="actual_start",
    )
    session.commit()
    session.refresh(sortie)
    return sortie


def mark_landed(session: Session, actor: User, sortie_id: int) -> Sortie:
    require_role(actor, [RoleEnum.DISPATCHER])
    sortie = get_sortie(session, actor, sortie_id)
    if sortie.status != SortieStatus.AIRBORNE:
        raise invalid_state(f"Cannot move sortie from {sortie.status.value} to LANDED")
    sortie.aircraft.status = AircraftStatus.LANDED
    _transition_sortie(
        session,
        actor=actor,
        sortie=sortie,
        allowed_from={SortieStatus.AIRBORNE},
        next_status=SortieStatus.LANDED,
        action="SORTIE_LANDED",
        actual_time_field="actual_end",
    )
    session.commit()
    session.refresh(sortie)
    return sortie


def cancel_sortie(session: Session, actor: User, sortie_id: int, payload: SortieCancelRequest) -> Sortie:
    require_role(actor, [RoleEnum.DISPATCHER])
    sortie = get_sortie(session, actor, sortie_id)
    if sortie.status in {SortieStatus.CLOSED, SortieStatus.CANCELLED}:
        raise invalid_state(f"Cannot move sortie from {sortie.status.value} to CANCELLED")
    old_value = {"status": sortie.status.value}
    sortie.status = SortieStatus.CANCELLED
    sortie.cancel_reason = payload.cancel_reason
    if sortie.aircraft.status == AircraftStatus.SCHEDULED:
        sortie.aircraft.status = AircraftStatus.READY
    session.flush()
    write_audit_log(
        session,
        actor=actor,
        action="SORTIE_CANCELLED",
        entity_type="sortie",
        entity_id=sortie.id,
        old_value=old_value,
        new_value={"status": sortie.status.value, "cancel_reason": sortie.cancel_reason},
        reason=payload.cancel_reason,
    )
    session.commit()
    session.refresh(sortie)
    return sortie


def close_sortie(session: Session, actor: User, sortie_id: int) -> Sortie:
    require_role(actor, [RoleEnum.DISPATCHER])
    sortie = get_sortie(session, actor, sortie_id)
    if sortie.status not in {SortieStatus.TRAINING_APPROVED, SortieStatus.RECOVERY_REQUIRED}:
        raise invalid_state(f"Cannot move sortie from {sortie.status.value} to CLOSED")
    progress = sortie.training_progress
    if progress is None or progress.status != TrainingStatus.APPROVED:
        raise invalid_state("Sortie cannot close before training approval")
    open_severe_defects = [
        defect
        for defect in sortie.aircraft.defects
        if defect.status == DefectStatus.OPEN and defect.severity in {DefectSeverity.HIGH, DefectSeverity.CRITICAL}
    ]
    if open_severe_defects:
        raise conflict("Sortie cannot close until defect recovery is completed")
    sortie.aircraft.status = AircraftStatus.READY
    _transition_sortie(
        session,
        actor=actor,
        sortie=sortie,
        allowed_from={SortieStatus.TRAINING_APPROVED, SortieStatus.RECOVERY_REQUIRED},
        next_status=SortieStatus.CLOSED,
        action="SORTIE_CLOSED",
    )
    session.commit()
    session.refresh(sortie)
    return sortie
