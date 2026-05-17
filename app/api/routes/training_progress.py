from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.schemas.training_progress import (
    TrainingProgressCreate,
    TrainingProgressResponse,
    TrainingRejectRequest,
    TrainingSubmitRequest,
)
from app.services.training_service import (
    approve_training_progress,
    create_training_progress,
    get_progress_by_sortie,
    reject_training_progress,
    submit_training_progress,
)

router = APIRouter(prefix="/training-progress", tags=["training-progress"])


@router.post("", response_model=TrainingProgressResponse)
def post_progress(
    payload: TrainingProgressCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TrainingProgressResponse:
    return TrainingProgressResponse.model_validate(create_training_progress(db, current_user, payload))


@router.get("/{sortie_id}", response_model=TrainingProgressResponse)
def get_progress(
    sortie_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TrainingProgressResponse:
    return TrainingProgressResponse.model_validate(get_progress_by_sortie(db, current_user, sortie_id))


@router.patch("/{progress_id}/submit", response_model=TrainingProgressResponse)
def patch_submit(
    progress_id: int,
    payload: TrainingSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TrainingProgressResponse:
    return TrainingProgressResponse.model_validate(submit_training_progress(db, current_user, progress_id, payload))


@router.patch("/{progress_id}/approve", response_model=TrainingProgressResponse)
def patch_approve(
    progress_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TrainingProgressResponse:
    return TrainingProgressResponse.model_validate(approve_training_progress(db, current_user, progress_id))


@router.patch("/{progress_id}/reject", response_model=TrainingProgressResponse)
def patch_reject(
    progress_id: int,
    payload: TrainingRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TrainingProgressResponse:
    return TrainingProgressResponse.model_validate(reject_training_progress(db, current_user, progress_id, payload))

