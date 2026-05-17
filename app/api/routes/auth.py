from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import not_found, unauthorized
from app.core.security import create_access_token, get_current_user
from app.db.database import get_db
from app.db.models import RoleEnum, User
from app.schemas.auth import AuthUserResponse, LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.scalar(select(User).where(User.email == payload.email, User.role == payload.role))
    if user is None:
        raise not_found("User not found")
    token = create_access_token(user=user)
    return LoginResponse(access_token=token, user=AuthUserResponse.model_validate(user))


@router.get("/me", response_model=AuthUserResponse)
def me(current_user: User = Depends(get_current_user)) -> AuthUserResponse:
    return AuthUserResponse.model_validate(current_user)

