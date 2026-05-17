from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AppError(Exception):
    code: str
    message: str
    status_code: int = 400
    field: str | None = None
    details: Any = None


def validation_error(message: str, field: str | None = None) -> AppError:
    return AppError(code="VALIDATION_ERROR", message=message, status_code=422, field=field)


def forbidden(message: str = "You do not have permission to perform this action") -> AppError:
    return AppError(code="FORBIDDEN", message=message, status_code=403)


def not_found(message: str = "Resource not found") -> AppError:
    return AppError(code="NOT_FOUND", message=message, status_code=404)


def conflict(message: str) -> AppError:
    return AppError(code="CONFLICT", message=message, status_code=409)


def invalid_state(message: str) -> AppError:
    return AppError(code="INVALID_STATE_TRANSITION", message=message, status_code=409)


def unauthorized(message: str = "Authentication required") -> AppError:
    return AppError(code="UNAUTHORIZED", message=message, status_code=401)

