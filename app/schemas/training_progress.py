from __future__ import annotations

from datetime import datetime

from pydantic import ConfigDict, Field

from app.db.models import TrainingStatus
from app.schemas.common import ORMModel


class TrainingProgressCreate(ORMModel):
    sortie_id: int = Field(description="Sortie being evaluated.", examples=[1])
    maneuver_score: int | None = Field(default=None, description="Maneuver score from 1 to 5.", examples=[4])
    communication_score: int | None = Field(default=None, description="Communication score from 1 to 5.", examples=[4])
    situational_awareness_score: int | None = Field(
        default=None, description="Situational awareness score from 1 to 5.", examples=[4]
    )
    remarks: str | None = Field(default=None, description="Initial remarks or draft comments.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sortie_id": 1,
                "maneuver_score": 4,
                "communication_score": 4,
                "situational_awareness_score": 4,
                "remarks": "Initial evaluation notes.",
            }
        }
    )


class TrainingProgressResponse(ORMModel):
    id: int
    sortie_id: int
    cadet_id: int
    instructor_id: int
    base_id: int
    lesson_type: str
    maneuver_score: int | None
    communication_score: int | None
    situational_awareness_score: int | None
    remarks: str | None
    status: TrainingStatus
    submitted_at: datetime | None
    approved_by: int | None
    approved_at: datetime | None
    rejection_reason: str | None


class TrainingSubmitRequest(ORMModel):
    maneuver_score: int = Field(ge=1, le=5, description="Maneuver score from 1 to 5.")
    communication_score: int = Field(ge=1, le=5, description="Communication score from 1 to 5.")
    situational_awareness_score: int = Field(
        ge=1, le=5, description="Situational awareness score from 1 to 5."
    )
    remarks: str = Field(min_length=1, description="Non-empty remarks required during submission.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "maneuver_score": 4,
                "communication_score": 5,
                "situational_awareness_score": 4,
                "remarks": "Strong handling and safe decision making.",
            }
        }
    )


class TrainingRejectRequest(ORMModel):
    rejection_reason: str = Field(min_length=1, description="Reason for rejection.")
