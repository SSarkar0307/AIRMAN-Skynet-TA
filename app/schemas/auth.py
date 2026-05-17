from __future__ import annotations

from pydantic import ConfigDict, Field

from app.db.models import RoleEnum
from app.schemas.common import ORMModel


class LoginRequest(ORMModel):
    email: str = Field(description="Registered user email.", examples=["dispatcher@airman.test"])
    role: RoleEnum = Field(description="User role selected for mock login.", examples=[RoleEnum.DISPATCHER.value])

    model_config = ConfigDict(
        json_schema_extra={"example": {"email": "dispatcher@airman.test", "role": "DISPATCHER"}}
    )


class AuthUserResponse(ORMModel):
    id: int
    full_name: str
    email: str
    role: RoleEnum
    base_id: int


class LoginResponse(ORMModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUserResponse
