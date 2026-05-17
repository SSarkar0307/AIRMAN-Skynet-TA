from __future__ import annotations

from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.db.models import AuditLog, User


def write_audit_log(
    session: Session,
    *,
    actor: User,
    action: str,
    entity_type: str,
    entity_id: int,
    old_value: Any = None,
    new_value: Any = None,
    reason: str | None = None,
) -> AuditLog:
    log = AuditLog(
        actor_id=actor.id,
        actor_role=actor.role.value,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=jsonable_encoder(old_value) if old_value is not None else None,
        new_value=jsonable_encoder(new_value) if new_value is not None else None,
        reason=reason,
    )
    session.add(log)
    session.flush()
    return log

