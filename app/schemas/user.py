from __future__ import annotations

from app.db.models import RoleEnum
from app.schemas.common import ORMModel


class UserResponse(ORMModel):
    id: int
    full_name: str
    email: str
    role: RoleEnum
    base_id: int
