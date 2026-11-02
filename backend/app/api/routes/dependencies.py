"""Read-only dependency graph and readiness routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.schemas.curriculum_api import ReadinessResponse, TopicDependencies
from app.services.dependency_queries import readiness, topic_dependencies


router = APIRouter(prefix="/api/v1/curriculum/releases/{release_id}", tags=["dependencies"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/topics/{topic_id}/dependencies", response_model=TopicDependencies)
def get_topic_dependencies(release_id: UUID, topic_id: str, session: SessionDep):
    return topic_dependencies(session, release_id, topic_id)


@router.get(
    "/learners/{learner_id}/topics/{topic_id}/readiness",
    response_model=ReadinessResponse,
)
def get_topic_readiness(release_id: UUID, learner_id: int, topic_id: str, session: SessionDep):
    return readiness(session, release_id, learner_id, topic_id)
