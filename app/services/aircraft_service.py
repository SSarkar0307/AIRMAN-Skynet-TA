from __future__ import annotations

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.errors import conflict, forbidden, not_found
from app.core.permissions import can_manage_aircraft, require_same_base
from app.db.models import Aircraft, AircraftStatus, Defect, DefectSeverity, DefectStatus, RoleEnum, Sortie, SortieStatus, User
from app.schemas.aircraft import AircraftCreate
from app.services.audit_service import write_audit_log


def list_aircraft(session: Session, actor: User) -> list[Aircraft]:
    query = select(Aircraft)
    if actor.role != RoleEnum.ADMIN:
        query = query.where(Aircraft.base_id == actor.base_id)
    return list(session.scalars(query.order_by(Aircraft.id)))


def get_aircraft(session: Session, actor: User, aircraft_id: int) -> Aircraft:
    aircraft = session.get(Aircraft, aircraft_id)
    if aircraft is None:
        raise not_found("Aircraft not found")
    if actor.role != RoleEnum.ADMIN and aircraft.base_id != actor.base_id:
        raise forbidden()
    return aircraft


def create_aircraft(session: Session, actor: User, payload: AircraftCreate) -> Aircraft:
    if actor.role != RoleEnum.ADMIN:
        raise forbidden()
    if session.scalar(select(Aircraft).where(Aircraft.registration == payload.registration)):
        raise conflict("Aircraft registration already exists")
    aircraft = Aircraft(
        registration=payload.registration,
        aircraft_type=payload.aircraft_type,
        base_id=payload.base_id,
        status=payload.status,
        tbo_remaining_hours=payload.tbo_remaining_hours,
    )
    session.add(aircraft)
    session.flush()
    write_audit_log(
        session,
        actor=actor,
        action="AIRCRAFT_CREATED",
        entity_type="aircraft",
        entity_id=aircraft.id,
        new_value={"registration": aircraft.registration, "status": aircraft.status.value},
    )
    session.commit()
    session.refresh(aircraft)
    return aircraft


def ground_aircraft(session: Session, actor: User, aircraft_id: int, reason: str | None = None) -> Aircraft:
    aircraft = get_aircraft(session, actor, aircraft_id)
    if actor.role not in {RoleEnum.ADMIN, RoleEnum.MAINTENANCE_OFFICER}:
        raise forbidden()
    old_value = {"status": aircraft.status.value}
    aircraft.status = AircraftStatus.GROUNDED
    session.flush()
    write_audit_log(
        session,
        actor=actor,
        action="AIRCRAFT_GROUNDED",
        entity_type="aircraft",
        entity_id=aircraft.id,
        old_value=old_value,
        new_value={"status": aircraft.status.value},
        reason=reason,
    )
    session.commit()
    session.refresh(aircraft)
    return aircraft


def mark_aircraft_ready(session: Session, actor: User, aircraft_id: int, reason: str | None = None) -> Aircraft:
    aircraft = get_aircraft(session, actor, aircraft_id)
    if actor.role not in {RoleEnum.ADMIN, RoleEnum.MAINTENANCE_OFFICER}:
        raise forbidden()
    open_severe = session.scalar(
        select(func.count(Defect.id)).where(
            Defect.aircraft_id == aircraft.id,
            Defect.status == DefectStatus.OPEN,
            Defect.severity.in_([DefectSeverity.HIGH, DefectSeverity.CRITICAL]),
        )
    )
    if open_severe:
        raise conflict("Aircraft cannot become ready until defect is resolved or deferred")
    old_value = {"status": aircraft.status.value}
    aircraft.status = AircraftStatus.READY
    session.flush()
    write_audit_log(
        session,
        actor=actor,
        action="AIRCRAFT_READY",
        entity_type="aircraft",
        entity_id=aircraft.id,
        old_value=old_value,
        new_value={"status": aircraft.status.value},
        reason=reason,
    )
    session.commit()
    session.refresh(aircraft)
    return aircraft


def set_aircraft_state_from_sortie(session: Session, sortie: Sortie, next_status: AircraftStatus) -> None:
    aircraft = sortie.aircraft
    aircraft.status = next_status
    session.flush()


def ensure_aircraft_assignable(session: Session, aircraft: Aircraft, start, end, *, sortie_id: int | None = None) -> None:
    if aircraft.status in {AircraftStatus.GROUNDED, AircraftStatus.MAINTENANCE}:
        raise conflict("Aircraft is grounded or under maintenance")
    conditions = [
        Sortie.aircraft_id == aircraft.id,
        Sortie.status != SortieStatus.CANCELLED,
        Sortie.scheduled_start < end,
        Sortie.scheduled_end > start,
    ]
    if sortie_id is not None:
        conditions.append(Sortie.id != sortie_id)
    overlapping = session.scalars(select(Sortie).where(and_(*conditions))).first()
    if overlapping is not None:
        raise conflict("Aircraft is already assigned to an overlapping sortie")
