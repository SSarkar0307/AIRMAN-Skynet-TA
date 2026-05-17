from __future__ import annotations

from datetime import datetime

from pydantic import ConfigDict, Field

from app.db.models import DefectSeverity, DefectStatus
from app.schemas.common import ORMModel


class DefectCreate(ORMModel):
    aircraft_id: int = Field(description="Aircraft that has the defect.", examples=[1])
    sortie_id: int | None = Field(default=None, description="Optional linked sortie id.", examples=[1])
    severity: DefectSeverity = Field(description="Severity classification.")
    description: str = Field(description="Free-text defect description.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "aircraft_id": 1,
                "sortie_id": 1,
                "severity": "CRITICAL",
                "description": "Engine oil pressure dropped below minimum during landing roll.",
            }
        }
    )


class DefectResponse(ORMModel):
    id: int
    aircraft_id: int
    sortie_id: int | None
    reported_by: int
    base_id: int
    severity: DefectSeverity
    description: str
    status: DefectStatus
    resolved_by: int | None
    resolved_at: datetime | None
    resolution_note: str | None


class DefectResolveRequest(ORMModel):
    resolution_note: str | None = Field(default=None, description="Resolution note.")


class DefectDeferRequest(ORMModel):
    resolution_note: str | None = Field(default=None, description="Deferment note.")
