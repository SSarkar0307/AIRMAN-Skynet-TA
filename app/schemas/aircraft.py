from __future__ import annotations

from pydantic import ConfigDict, Field

from app.db.models import AircraftStatus
from app.schemas.common import ORMModel


class AircraftCreate(ORMModel):
    registration: str = Field(description="Unique aircraft registration.", examples=["VT-ABC"])
    aircraft_type: str = Field(description="Aircraft make and model.", examples=["Cessna 172"])
    base_id: int = Field(description="Owning base identifier.", examples=[1])
    status: AircraftStatus = Field(default=AircraftStatus.READY, description="Initial readiness state.")
    tbo_remaining_hours: int = Field(default=0, description="Maintenance hours remaining before TBO.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "registration": "VT-NEW",
                "aircraft_type": "Cessna 152",
                "base_id": 1,
                "status": "READY",
                "tbo_remaining_hours": 120,
            }
        }
    )


class AircraftResponse(ORMModel):
    id: int
    registration: str
    aircraft_type: str
    base_id: int
    status: AircraftStatus
    tbo_remaining_hours: int
