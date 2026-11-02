"""Learner progress read and mutation routes."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.schemas.api_common import ItemList
from app.schemas.learner_api import ProgressEnvelope, ProgressPatch, ProgressResponse
from app.services import progress_service


router = APIRouter(prefix="/api/v1/curriculum/releases/{release_id}/learners/{learner_id}", tags=["learner-progress"])
SessionDep = Annotated[Session, Depends(get_session)]
ProgressStatusQuery = Literal["Not started", "Learning", "Practicing", "Solid", "Revisit"]


@router.get("/progress", response_model=ItemList[ProgressResponse])
def list_progress(
    release_id: UUID,
    learner_id: int,
    session: SessionDep,
    progress_status: ProgressStatusQuery | None = None,
):
    return progress_service.list_progress(session, release_id, learner_id, progress_status=progress_status)


@router.get("/progress/{topic_id}", response_model=ProgressEnvelope)
def get_progress(release_id: UUID, learner_id: int, topic_id: str, session: SessionDep):
    return progress_service.get_progress(session, release_id, learner_id, topic_id)


@router.patch("/progress/{topic_id}", response_model=ProgressEnvelope)
def patch_progress(release_id: UUID, learner_id: int, topic_id: str, body: ProgressPatch, session: SessionDep):
    return progress_service.patch_progress(session, release_id, learner_id, topic_id, body)


@router.delete("/progress/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
def clear_progress(release_id: UUID, learner_id: int, topic_id: str, session: SessionDep):
    progress_service.clear_progress(session, release_id, learner_id, topic_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
