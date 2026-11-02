"""Local learner discovery route."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.schemas.learner_api import LearnerResponse
from app.services import learner_service


router = APIRouter(prefix="/api/v1/learners", tags=["learners"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/current", response_model=LearnerResponse)
def current_learner(session: SessionDep):
    return learner_service.get_current_learner(session)
