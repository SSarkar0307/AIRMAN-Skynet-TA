from __future__ import annotations

from typing import Iterable

from sqlalchemy.orm import Session

from app.core.errors import forbidden
from app.db.models import Aircraft, Defect, RoleEnum, Sortie, TrainingProgress, TrainingStatus, User


def is_admin(user: User) -> bool:
    return user.role == RoleEnum.ADMIN


def require_role(user: User, allowed_roles: Iterable[RoleEnum]) -> None:
    if is_admin(user):
        return
    if user.role not in set(allowed_roles):
        raise forbidden()


def require_same_base(user: User, base_id: int) -> None:
    if is_admin(user):
        return
    if user.base_id != base_id:
        raise forbidden()


def require_base_or_assigned(user: User, base_id: int) -> None:
    if is_admin(user):
        return
    if user.base_id != base_id:
        raise forbidden()


def can_view_sortie(user: User, sortie: Sortie) -> bool:
    if is_admin(user):
        return True
    if user.base_id != sortie.base_id:
        return False
    if user.role in {RoleEnum.DISPATCHER, RoleEnum.MAINTENANCE_OFFICER, RoleEnum.CFI}:
        return True
    if user.role == RoleEnum.INSTRUCTOR and sortie.instructor_id == user.id:
        return True
    if user.role == RoleEnum.CADET and sortie.cadet_id == user.id:
        return True
    return False


def can_view_training_progress(user: User, progress: TrainingProgress) -> bool:
    if is_admin(user):
        return True
    if user.base_id != progress.base_id:
        return False
    if user.role == RoleEnum.CFI:
        return True
    if user.role == RoleEnum.INSTRUCTOR and progress.instructor_id == user.id:
        return True
    if user.role == RoleEnum.CADET:
        return progress.status == TrainingStatus.APPROVED and progress.cadet_id == user.id
    return False


def can_manage_defect(user: User, defect: Defect) -> bool:
    if is_admin(user):
        return True
    if user.base_id != defect.base_id:
        return False
    return user.role in {RoleEnum.MAINTENANCE_OFFICER, RoleEnum.DISPATCHER, RoleEnum.INSTRUCTOR}


def can_manage_aircraft(user: User, aircraft: Aircraft) -> bool:
    if is_admin(user):
        return True
    return user.base_id == aircraft.base_id and user.role == RoleEnum.MAINTENANCE_OFFICER
