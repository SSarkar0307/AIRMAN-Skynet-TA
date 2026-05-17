from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import conflict, forbidden, invalid_state, not_found, validation_error
from app.core.permissions import can_view_training_progress, require_role
from app.db.models import RoleEnum, Sortie, SortieStatus, TrainingProgress, TrainingStatus, User
from app.schemas.training_progress import TrainingProgressCreate, TrainingRejectRequest, TrainingSubmitRequest
from app.services.audit_service import write_audit_log


def get_progress_by_sortie(session: Session, actor: User, sortie_id: int) -> TrainingProgress:
    progress = session.scalar(select(TrainingProgress).where(TrainingProgress.sortie_id == sortie_id))
    if progress is None:
        raise not_found("Training progress not found")
    if not can_view_training_progress(actor, progress):
        raise forbidden()
    return progress


def create_training_progress(session: Session, actor: User, payload: TrainingProgressCreate) -> TrainingProgress:
    require_role(actor, [RoleEnum.INSTRUCTOR])
    sortie = session.get(Sortie, payload.sortie_id)
    if sortie is None:
        raise not_found("Sortie not found")
    if sortie.instructor_id != actor.id and actor.role != RoleEnum.ADMIN:
        raise forbidden()
    if session.scalar(select(TrainingProgress).where(TrainingProgress.sortie_id == sortie.id)):
        raise conflict("Training progress already exists for this sortie")
    progress = TrainingProgress(
        sortie_id=sortie.id,
        cadet_id=sortie.cadet_id,
        instructor_id=sortie.instructor_id,
        base_id=sortie.base_id,
        lesson_type=sortie.lesson_type,
        maneuver_score=payload.maneuver_score,
        communication_score=payload.communication_score,
        situational_awareness_score=payload.situational_awareness_score,
        remarks=payload.remarks,
        status=TrainingStatus.DRAFT,
    )
    session.add(progress)
    session.flush()
    write_audit_log(
        session,
        actor=actor,
        action="TRAINING_DRAFT_CREATED",
        entity_type="training_progress",
        entity_id=progress.id,
        new_value={"sortie_id": progress.sortie_id, "status": progress.status.value},
    )
    session.commit()
    session.refresh(progress)
    return progress


def _validate_scores(payload: TrainingSubmitRequest) -> None:
    for field_name, value in payload.model_dump().items():
        if field_name == "remarks":
            if not value or not str(value).strip():
                raise validation_error("Remarks cannot be empty during submission", field="remarks")
            continue
        if value < 1 or value > 5:
            raise validation_error("Score must be between 1 and 5", field=field_name)


def submit_training_progress(session: Session, actor: User, progress_id: int, payload: TrainingSubmitRequest) -> TrainingProgress:
    progress = session.get(TrainingProgress, progress_id)
    if progress is None:
        raise not_found("Training progress not found")
    if actor.role not in {RoleEnum.INSTRUCTOR, RoleEnum.ADMIN} or (
        actor.role != RoleEnum.ADMIN and progress.instructor_id != actor.id
    ):
        raise forbidden()
    _validate_scores(payload)
    if progress.status not in {TrainingStatus.DRAFT, TrainingStatus.REJECTED}:
        raise invalid_state(f"Cannot move training progress from {progress.status.value} to SUBMITTED")
    old_value = {"status": progress.status.value}
    progress.maneuver_score = payload.maneuver_score
    progress.communication_score = payload.communication_score
    progress.situational_awareness_score = payload.situational_awareness_score
    progress.remarks = payload.remarks
    progress.status = TrainingStatus.SUBMITTED
    progress.submitted_at = datetime.now(timezone.utc)
    if progress.sortie.status in {SortieStatus.LANDED, SortieStatus.AIRCRAFT_GROUNDED, SortieStatus.RECOVERY_REQUIRED}:
        progress.sortie.status = SortieStatus.TRAINING_SUBMITTED
    session.flush()
    write_audit_log(
        session,
        actor=actor,
        action="TRAINING_SUBMITTED",
        entity_type="training_progress",
        entity_id=progress.id,
        old_value=old_value,
        new_value={"status": progress.status.value},
    )
    session.commit()
    session.refresh(progress)
    return progress


def approve_training_progress(session: Session, actor: User, progress_id: int) -> TrainingProgress:
    progress = session.get(TrainingProgress, progress_id)
    if progress is None:
        raise not_found("Training progress not found")
    if actor.role not in {RoleEnum.CFI, RoleEnum.ADMIN} or (
        actor.role != RoleEnum.ADMIN and progress.base_id != actor.base_id
    ):
        raise forbidden()
    if progress.status != TrainingStatus.SUBMITTED:
        raise invalid_state(f"Cannot move training progress from {progress.status.value} to APPROVED")
    old_value = {"status": progress.status.value}
    progress.status = TrainingStatus.APPROVED
    progress.approved_by = actor.id
    progress.approved_at = datetime.now(timezone.utc)
    progress.rejection_reason = None
    progress.sortie.status = SortieStatus.TRAINING_APPROVED
    session.flush()
    write_audit_log(
        session,
        actor=actor,
        action="TRAINING_APPROVED",
        entity_type="training_progress",
        entity_id=progress.id,
        old_value=old_value,
        new_value={"status": progress.status.value},
    )
    session.commit()
    session.refresh(progress)
    return progress


def reject_training_progress(session: Session, actor: User, progress_id: int, payload: TrainingRejectRequest) -> TrainingProgress:
    progress = session.get(TrainingProgress, progress_id)
    if progress is None:
        raise not_found("Training progress not found")
    if actor.role not in {RoleEnum.CFI, RoleEnum.ADMIN} or (
        actor.role != RoleEnum.ADMIN and progress.base_id != actor.base_id
    ):
        raise forbidden()
    if progress.status != TrainingStatus.SUBMITTED:
        raise invalid_state(f"Cannot move training progress from {progress.status.value} to REJECTED")
    old_value = {"status": progress.status.value}
    progress.status = TrainingStatus.REJECTED
    progress.rejection_reason = payload.rejection_reason
    progress.approved_by = None
    progress.approved_at = None
    progress.sortie.status = SortieStatus.LANDED
    session.flush()
    write_audit_log(
        session,
        actor=actor,
        action="TRAINING_REJECTED",
        entity_type="training_progress",
        entity_id=progress.id,
        old_value=old_value,
        new_value={"status": progress.status.value},
        reason=payload.rejection_reason,
    )
    session.commit()
    session.refresh(progress)
    return progress
