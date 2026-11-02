"""Release and curriculum read routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.schemas.api_common import ItemList
from app.schemas.curriculum_api import (
    CurriculumHierarchy,
    PhaseResponse,
    ReleaseDetail,
    ReleaseSummary,
    TopicDetail,
    TopicSummary,
    TrackResponse,
)
from app.schemas.learner_api import ActiveReleaseSelection
from app.services import curriculum_queries, release_selection
from app.services.dependency_queries import readiness as query_readiness


router = APIRouter(prefix="/api/v1/curriculum", tags=["curriculum"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/releases", response_model=ItemList[ReleaseSummary])
def releases(session: SessionDep):
    return curriculum_queries.list_releases(session)


@router.get("/active-release", response_model=ReleaseSummary)
def active_release(session: SessionDep):
    return release_selection.get_active_release(session)


@router.put("/active-release", response_model=ReleaseSummary)
def select_active_release(body: ActiveReleaseSelection, session: SessionDep):
    return release_selection.select_active_release(session, body.release_id)


@router.get("/releases/{release_id}", response_model=ReleaseDetail)
def release_detail(release_id: UUID, session: SessionDep):
    return curriculum_queries.release_detail(session, release_id)


@router.get("/releases/{release_id}/tracks", response_model=ItemList[TrackResponse])
def tracks(release_id: UUID, session: SessionDep):
    return curriculum_queries.list_tracks(session, release_id)


@router.get("/releases/{release_id}/phases", response_model=ItemList[PhaseResponse])
def phases(release_id: UUID, session: SessionDep):
    return curriculum_queries.list_phases(session, release_id)


@router.get("/releases/{release_id}/topics", response_model=ItemList[TopicSummary])
def topics(
    release_id: UUID,
    session: SessionDep,
    track_id: str | None = None,
    phase_id: str | None = None,
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
):
    return curriculum_queries.list_topics(
        session,
        release_id,
        track_id=track_id,
        phase_id=phase_id,
        cursor=cursor,
        limit=limit,
    )


@router.get("/releases/{release_id}/hierarchy", response_model=CurriculumHierarchy)
def hierarchy(release_id: UUID, session: SessionDep):
    return curriculum_queries.curriculum_hierarchy(session, release_id)


@router.get("/releases/{release_id}/topics/{topic_id}", response_model=TopicDetail)
def topic(release_id: UUID, topic_id: str, session: SessionDep):
    return curriculum_queries.topic_detail(session, release_id, topic_id)
