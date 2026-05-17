from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class RoleEnum(str, Enum):
    ADMIN = "ADMIN"
    DISPATCHER = "DISPATCHER"
    INSTRUCTOR = "INSTRUCTOR"
    CFI = "CFI"
    CADET = "CADET"
    MAINTENANCE_OFFICER = "MAINTENANCE_OFFICER"


class AircraftStatus(str, Enum):
    READY = "READY"
    SCHEDULED = "SCHEDULED"
    AIRBORNE = "AIRBORNE"
    LANDED = "LANDED"
    GROUNDED = "GROUNDED"
    MAINTENANCE = "MAINTENANCE"


class SortieStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    RELEASED = "RELEASED"
    AIRBORNE = "AIRBORNE"
    LANDED = "LANDED"
    TRAINING_SUBMITTED = "TRAINING_SUBMITTED"
    TRAINING_APPROVED = "TRAINING_APPROVED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"
    AIRCRAFT_GROUNDED = "AIRCRAFT_GROUNDED"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


class TrainingStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class DefectSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DefectStatus(str, Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    DEFERRED = "DEFERRED"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class BaseEntity(Base, TimestampMixin):
    __abstract__ = True
    id: Mapped[int] = mapped_column(Integer, primary_key=True)


class AviationBase(BaseEntity):
    __tablename__ = "bases"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    location: Mapped[str] = mapped_column(String(120), nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="base")
    aircraft: Mapped[list["Aircraft"]] = relationship(back_populates="base")
    sorties: Mapped[list["Sortie"]] = relationship(back_populates="base")


class User(BaseEntity):
    __tablename__ = "users"

    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    role: Mapped[RoleEnum] = mapped_column(SAEnum(RoleEnum, native_enum=False), nullable=False, index=True)
    base_id: Mapped[int] = mapped_column(ForeignKey("bases.id"), nullable=False, index=True)

    base: Mapped[AviationBase] = relationship(back_populates="users")
    cadet_sorties: Mapped[list["Sortie"]] = relationship(foreign_keys="Sortie.cadet_id", back_populates="cadet")
    instructor_sorties: Mapped[list["Sortie"]] = relationship(
        foreign_keys="Sortie.instructor_id", back_populates="instructor"
    )


class Aircraft(BaseEntity):
    __tablename__ = "aircraft"

    registration: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    aircraft_type: Mapped[str] = mapped_column(String(80), nullable=False)
    base_id: Mapped[int] = mapped_column(ForeignKey("bases.id"), nullable=False, index=True)
    status: Mapped[AircraftStatus] = mapped_column(
        SAEnum(AircraftStatus, native_enum=False), default=AircraftStatus.READY, nullable=False, index=True
    )
    tbo_remaining_hours: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    base: Mapped[AviationBase] = relationship(back_populates="aircraft")
    sorties: Mapped[list["Sortie"]] = relationship(back_populates="aircraft")
    defects: Mapped[list["Defect"]] = relationship(back_populates="aircraft")


class Sortie(BaseEntity):
    __tablename__ = "sorties"
    __table_args__ = (
        UniqueConstraint("sortie_number", name="uq_sortie_number"),
    )

    sortie_number: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    cadet_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    instructor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    aircraft_id: Mapped[int] = mapped_column(ForeignKey("aircraft.id"), nullable=False, index=True)
    base_id: Mapped[int] = mapped_column(ForeignKey("bases.id"), nullable=False, index=True)
    lesson_type: Mapped[str] = mapped_column(String(80), nullable=False)
    scheduled_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    scheduled_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    actual_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    actual_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[SortieStatus] = mapped_column(
        SAEnum(SortieStatus, native_enum=False), default=SortieStatus.SCHEDULED, nullable=False, index=True
    )
    delay_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    base: Mapped[AviationBase] = relationship(back_populates="sorties")
    cadet: Mapped[User] = relationship(foreign_keys=[cadet_id], back_populates="cadet_sorties")
    instructor: Mapped[User] = relationship(foreign_keys=[instructor_id], back_populates="instructor_sorties")
    aircraft: Mapped[Aircraft] = relationship(back_populates="sorties")
    training_progress: Mapped["TrainingProgress"] = relationship(back_populates="sortie", uselist=False)
    defects: Mapped[list["Defect"]] = relationship(back_populates="sortie")


class TrainingProgress(BaseEntity):
    __tablename__ = "training_progress"

    sortie_id: Mapped[int] = mapped_column(ForeignKey("sorties.id"), unique=True, nullable=False, index=True)
    cadet_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    instructor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    base_id: Mapped[int] = mapped_column(ForeignKey("bases.id"), nullable=False, index=True)
    lesson_type: Mapped[str] = mapped_column(String(80), nullable=False)
    maneuver_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    communication_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    situational_awareness_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[TrainingStatus] = mapped_column(
        SAEnum(TrainingStatus, native_enum=False), default=TrainingStatus.DRAFT, nullable=False, index=True
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    sortie: Mapped[Sortie] = relationship(back_populates="training_progress")
    cadet: Mapped[User] = relationship(foreign_keys=[cadet_id])
    instructor: Mapped[User] = relationship(foreign_keys=[instructor_id])
    approver: Mapped[User | None] = relationship(foreign_keys=[approved_by])
    base: Mapped[AviationBase] = relationship()


class Defect(BaseEntity):
    __tablename__ = "defects"

    aircraft_id: Mapped[int] = mapped_column(ForeignKey("aircraft.id"), nullable=False, index=True)
    sortie_id: Mapped[int | None] = mapped_column(ForeignKey("sorties.id"), nullable=True, index=True)
    reported_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    base_id: Mapped[int] = mapped_column(ForeignKey("bases.id"), nullable=False, index=True)
    severity: Mapped[DefectSeverity] = mapped_column(
        SAEnum(DefectSeverity, native_enum=False), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[DefectStatus] = mapped_column(
        SAEnum(DefectStatus, native_enum=False), default=DefectStatus.OPEN, nullable=False, index=True
    )
    resolved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    aircraft: Mapped[Aircraft] = relationship(back_populates="defects")
    sortie: Mapped[Sortie | None] = relationship(back_populates="defects")
    reporter: Mapped[User] = relationship(foreign_keys=[reported_by])
    resolver: Mapped[User | None] = relationship(foreign_keys=[resolved_by])


class AuditLog(BaseEntity):
    __tablename__ = "audit_logs"

    actor_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    actor_role: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    old_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )
