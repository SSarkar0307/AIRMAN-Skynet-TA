from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.common import ORMModel


class AuditLogResponse(ORMModel):
    id: int = Field(description="Audit record id.")
    actor_id: int = Field(description="Actor user id.")
    actor_role: str = Field(description="Actor role.")
    action: str = Field(description="Action performed.")
    entity_type: str = Field(description="Affected entity type.")
    entity_id: int = Field(description="Affected entity id.")
    old_value: dict | None = Field(default=None, description="State before change.")
    new_value: dict | None = Field(default=None, description="State after change.")
    reason: str | None = Field(default=None, description="Optional human reason.")
    timestamp: datetime = Field(description="Timestamp of the audit event.")
