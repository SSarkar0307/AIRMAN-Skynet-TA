from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db.models import (
    Aircraft,
    AircraftStatus,
    AviationBase,
    AuditLog,
    Defect,
    DefectSeverity,
    DefectStatus,
    RoleEnum,
    Sortie,
    SortieStatus,
    TrainingProgress,
    TrainingStatus,
    User,
)


def seed_demo_data(session: Session) -> None:
    if session.query(User).first():
        return

    delhi = AviationBase(name="Delhi Base", code="DEL", location="Delhi")
    mumbai = AviationBase(name="Mumbai Base", code="MUM", location="Mumbai")
    session.add_all([delhi, mumbai])
    session.flush()

    admin = User(full_name="Admin User", email="admin@airman.test", role=RoleEnum.ADMIN, base_id=delhi.id)
    dispatcher = User(
        full_name="Dispatch Officer", email="dispatcher@airman.test", role=RoleEnum.DISPATCHER, base_id=delhi.id
    )
    instructor = User(full_name="Capt. Rao", email="rao@airman.test", role=RoleEnum.INSTRUCTOR, base_id=delhi.id)
    cfi = User(
        full_name="Chief Flying Instructor", email="cfi@airman.test", role=RoleEnum.CFI, base_id=delhi.id
    )
    cadet = User(full_name="Arjun Menon", email="arjun@airman.test", role=RoleEnum.CADET, base_id=delhi.id)
    maint = User(
        full_name="Maintenance Officer", email="maint@airman.test", role=RoleEnum.MAINTENANCE_OFFICER, base_id=delhi.id
    )
    session.add_all([admin, dispatcher, instructor, cfi, cadet, maint])
    session.flush()

    aircraft_ready = Aircraft(
        registration="VT-ABC",
        aircraft_type="Cessna 172",
        base_id=delhi.id,
        status=AircraftStatus.READY,
        tbo_remaining_hours=120,
    )
    aircraft_grounded = Aircraft(
        registration="VT-SKY",
        aircraft_type="Piper PA-28",
        base_id=delhi.id,
        status=AircraftStatus.GROUNDED,
        tbo_remaining_hours=45,
    )
    aircraft_mumbai = Aircraft(
        registration="VT-AIR",
        aircraft_type="Diamond DA40",
        base_id=mumbai.id,
        status=AircraftStatus.READY,
        tbo_remaining_hours=98,
    )
    session.add_all([aircraft_ready, aircraft_grounded, aircraft_mumbai])
    session.flush()

    now = datetime.now(timezone.utc)
    sorties = [
        Sortie(
            sortie_number="S001",
            cadet_id=cadet.id,
            instructor_id=instructor.id,
            aircraft_id=aircraft_ready.id,
            base_id=delhi.id,
            lesson_type="Circuit Pattern",
            scheduled_start=now + timedelta(hours=1),
            scheduled_end=now + timedelta(hours=2),
            status=SortieStatus.SCHEDULED,
        ),
        Sortie(
            sortie_number="S002",
            cadet_id=cadet.id,
            instructor_id=instructor.id,
            aircraft_id=aircraft_ready.id,
            base_id=delhi.id,
            lesson_type="Stalls",
            scheduled_start=now - timedelta(hours=2),
            scheduled_end=now - timedelta(hours=1, minutes=30),
            actual_start=now - timedelta(hours=2),
            status=SortieStatus.RELEASED,
        ),
        Sortie(
            sortie_number="S003",
            cadet_id=cadet.id,
            instructor_id=instructor.id,
            aircraft_id=aircraft_grounded.id,
            base_id=delhi.id,
            lesson_type="Airwork",
            scheduled_start=now - timedelta(hours=3),
            scheduled_end=now - timedelta(hours=2),
            actual_start=now - timedelta(hours=3),
            actual_end=now - timedelta(hours=2, minutes=15),
            status=SortieStatus.AIRBORNE,
        ),
        Sortie(
            sortie_number="S004",
            cadet_id=cadet.id,
            instructor_id=instructor.id,
            aircraft_id=aircraft_ready.id,
            base_id=delhi.id,
            lesson_type="Nav",
            scheduled_start=now - timedelta(days=1),
            scheduled_end=now - timedelta(days=1, hours=-1),
            actual_start=now - timedelta(days=1),
            actual_end=now - timedelta(days=1, minutes=-45),
            status=SortieStatus.LANDED,
        ),
        Sortie(
            sortie_number="S005",
            cadet_id=cadet.id,
            instructor_id=instructor.id,
            aircraft_id=aircraft_grounded.id,
            base_id=delhi.id,
            lesson_type="Checkride Prep",
            scheduled_start=now - timedelta(days=2),
            scheduled_end=now - timedelta(days=2, hours=-1),
            actual_start=now - timedelta(days=2),
            actual_end=now - timedelta(days=2, minutes=-50),
            status=SortieStatus.TRAINING_SUBMITTED,
        ),
    ]
    session.add_all(sorties)
    session.flush()

    tp1 = TrainingProgress(
        sortie_id=sorties[3].id,
        cadet_id=cadet.id,
        instructor_id=instructor.id,
        base_id=delhi.id,
        lesson_type="Nav",
        maneuver_score=4,
        communication_score=5,
        situational_awareness_score=4,
        remarks="Solid navigation work.",
        status=TrainingStatus.APPROVED,
        submitted_at=now - timedelta(days=1, hours=1),
        approved_by=cfi.id,
        approved_at=now - timedelta(days=1),
    )
    tp2 = TrainingProgress(
        sortie_id=sorties[4].id,
        cadet_id=cadet.id,
        instructor_id=instructor.id,
        base_id=delhi.id,
        lesson_type="Checkride Prep",
        maneuver_score=3,
        communication_score=4,
        situational_awareness_score=3,
        remarks="Needs more radio discipline.",
        status=TrainingStatus.SUBMITTED,
        submitted_at=now - timedelta(days=2, hours=1),
    )
    session.add_all([tp1, tp2])
    session.flush()

    defect1 = Defect(
        aircraft_id=aircraft_grounded.id,
        sortie_id=sorties[4].id,
        reported_by=maint.id,
        base_id=delhi.id,
        severity=DefectSeverity.CRITICAL,
        description="Engine oil pressure abnormal.",
        status=DefectStatus.OPEN,
    )
    defect2 = Defect(
        aircraft_id=aircraft_ready.id,
        sortie_id=sorties[3].id,
        reported_by=dispatcher.id,
        base_id=delhi.id,
        severity=DefectSeverity.LOW,
        description="Cabin light flicker reported.",
        status=DefectStatus.RESOLVED,
        resolved_by=maint.id,
        resolved_at=now - timedelta(days=1, minutes=30),
    )
    session.add_all([defect1, defect2])

    session.add(
        AuditLog(
            actor_id=admin.id,
            actor_role=admin.role.value,
            action="SEED",
            entity_type="system",
            entity_id=0,
            old_value=None,
            new_value={"seeded": True},
            reason="Initial dataset",
        )
    )
    session.commit()
