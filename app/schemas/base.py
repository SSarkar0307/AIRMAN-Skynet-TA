from __future__ import annotations

from app.schemas.common import ORMModel


class BaseResponse(ORMModel):
    id: int
    name: str
    code: str
    location: str

