from __future__ import annotations

from datetime import datetime

from pydantic import ConfigDict, Field

from app.db.models import SortieStatus
from app.schemas.common import ORMModel


class SortieCreate(ORMModel):
    sortie_number: str = Field(description="Unique sortie identifier.", examples=["S1001"])
    cadet_id: int = Field(description="Assigned cadet user id.", examples=[5])
    instructor_id: int = Field(description="Assigned instructor user id.", examples=[3])
    aircraft_id: int = Field(description="Aircraft used for the sortie.", examples=[1])
    base_id: int = Field(description="Base where the sortie belongs.", examples=[1])
    lesson_type: str = Field(description="Training lesson type.", examples=["Circuit Pattern"])
    scheduled_start: datetime = Field(description="Planned sortie start timestamp.")
    scheduled_end: datetime = Field(description="Planned sortie end timestamp.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sortie_number": "S1001",
                "cadet_id": 5,
                "instructor_id": 3,
                "aircraft_id": 1,
                "base_id": 1,
                "lesson_type": "Circuit Pattern",
                "scheduled_start": "2026-05-17T06:00:00Z",
                "scheduled_end": "2026-05-17T07:00:00Z",
            }
        }
    )


class SortieResponse(ORMModel):
    id: int
    sortie_number: str
    cadet_id: int
    instructor_id: int
    aircraft_id: int
    base_id: int
    lesson_type: str
    scheduled_start: datetime
    scheduled_end: datetime
    actual_start: datetime | None
    actual_end: datetime | None
    status: SortieStatus
    delay_minutes: int | None
    cancel_reason: str | None
    version: int


class SortieCancelRequest(ORMModel):
    cancel_reason: str | None = Field(default=None, description="Reason for cancellation.")
