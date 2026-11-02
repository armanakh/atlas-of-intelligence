"""Release-scoped curriculum read models."""

from __future__ import annotations

import base64
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.errors import APIError
from app.db.models import (
    CurriculumRelease,
    LearningObjective,
    PhaseVersion,
    PrerequisiteGroup,
    PrerequisiteMember,
    RelatedTopic,
    TopicPhasePlacement,
    TopicTrackMembership,
    TopicVersion,
    TrackVersion,
)
from app.schemas.api_common import ItemList
from app.schemas.curriculum_api import (
    CurriculumHierarchy,
    HierarchyPhase,
    HierarchyTrack,
    ObjectiveResponse,
    PhaseResponse,
    PrerequisiteGroupResponse,
    ReleaseDetail,
    ReleaseSummary,
    TopicDetail,
    TopicSummary,
    TrackResponse,
)
from app.services.release_resolver import require_topic, resolve_release
from app.services.release_selection import _summary


_TOPIC_FIELDS = {
    "id", "title", "description", "pathway", "current_priority", "registry_status",
    "dependency_review_status", "track_ids", "phase_id", "objectives",
    "prerequisite_groups", "related_topic_ids",
}


def _metadata(payload: dict[str, Any], known: set[str]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key not in known}


def _track(row: TrackVersion) -> TrackResponse:
    return TrackResponse(
        id=row.track_id,
        title=row.title,
        metadata=_metadata(row.source_payload, {"id", "title"}),
    )


def _phase(row: PhaseVersion) -> PhaseResponse:
    return PhaseResponse(
        id=row.phase_id,
        title=row.title,
        metadata=_metadata(row.source_payload, {"id", "title"}),
    )


def _topic_summary(row: TopicVersion, track_ids: list[str], phase_id: str | None) -> TopicSummary:
    payload = row.source_payload
    return TopicSummary(
        id=row.topic_id,
        title=row.title,
        description=row.description,
        track_ids=track_ids,
        phase_id=phase_id,
        current_priority=row.current_priority,
        metadata=_metadata(payload, _TOPIC_FIELDS),
    )


def list_releases(session: Session) -> ItemList[ReleaseSummary]:
    rows = session.scalars(select(CurriculumRelease).order_by(CurriculumRelease.imported_at.desc(), CurriculumRelease.id)).all()
    return ItemList[ReleaseSummary](items=[_summary(row) for row in rows], next_cursor=None)


def release_detail(session: Session, public_id: UUID) -> ReleaseDetail:
    release = resolve_release(session, public_id)
    rid = release.id
    counts = [
        session.scalar(select(func.count()).select_from(model).where(column == rid)) or 0
        for model, column in (
            (TrackVersion, TrackVersion.release_id),
            (PhaseVersion, PhaseVersion.release_id),
            (TopicVersion, TopicVersion.release_id),
        )
    ]
    return ReleaseDetail(
        **_summary(release).model_dump(),
        track_count=counts[0],
        phase_count=counts[1],
        topic_count=counts[2],
    )


def list_tracks(session: Session, public_id: UUID) -> ItemList[TrackResponse]:
    release = resolve_release(session, public_id)
    rows = session.scalars(
        select(TrackVersion).where(TrackVersion.release_id == release.id).order_by(TrackVersion.track_id)
    ).all()
    return ItemList[TrackResponse](items=[_track(row) for row in rows], next_cursor=None)


def list_phases(session: Session, public_id: UUID) -> ItemList[PhaseResponse]:
    release = resolve_release(session, public_id)
    rows = session.scalars(
        select(PhaseVersion).where(PhaseVersion.release_id == release.id).order_by(PhaseVersion.phase_id)
    ).all()
    return ItemList[PhaseResponse](items=[_phase(row) for row in rows], next_cursor=None)


def _decode_cursor(cursor: str | None) -> int:
    if cursor is None:
        return 0
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode("ascii")
        offset = int(raw)
    except (ValueError, UnicodeDecodeError):
        raise APIError(400, "invalid_cursor", "The pagination cursor is malformed") from None
    if offset < 0:
        raise APIError(400, "invalid_cursor", "The pagination cursor is malformed")
    return offset


def _encode_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(str(offset).encode("ascii")).decode("ascii").rstrip("=")


def list_topics(
    session: Session,
    public_id: UUID,
    *,
    track_id: str | None,
    phase_id: str | None,
    cursor: str | None,
    limit: int,
) -> ItemList[TopicSummary]:
    release = resolve_release(session, public_id)
    rid = release.id
    offset = _decode_cursor(cursor)
    if track_id is not None and session.get(TrackVersion, (rid, track_id)) is None:
        raise APIError(404, "track_not_found", f"Track {track_id!r} is not in this release")
    if phase_id is not None and session.get(PhaseVersion, (rid, phase_id)) is None:
        raise APIError(404, "phase_not_found", f"Phase {phase_id!r} is not in this release")

    statement = select(TopicVersion).where(TopicVersion.release_id == rid)
    if track_id is not None:
        statement = statement.where(
            select(TopicTrackMembership.topic_id)
            .where(
                TopicTrackMembership.release_id == rid,
                TopicTrackMembership.topic_id == TopicVersion.topic_id,
                TopicTrackMembership.track_id == track_id,
            )
            .exists()
        )
    if phase_id is not None:
        statement = statement.where(
            select(TopicPhasePlacement.topic_id)
            .where(
                TopicPhasePlacement.release_id == rid,
                TopicPhasePlacement.topic_id == TopicVersion.topic_id,
                TopicPhasePlacement.phase_id == phase_id,
            )
            .exists()
        )
    topics = session.scalars(statement.order_by(TopicVersion.topic_id).offset(offset).limit(limit + 1)).all()
    next_cursor = _encode_cursor(offset + limit) if len(topics) > limit else None
    topics = topics[:limit]
    results: list[TopicSummary] = []
    for topic in topics:
        track_ids = session.scalars(
            select(TopicTrackMembership.track_id)
            .where(TopicTrackMembership.release_id == rid, TopicTrackMembership.topic_id == topic.topic_id)
            .order_by(TopicTrackMembership.track_id)
        ).all()
        phase_id_for_topic = session.scalar(
            select(TopicPhasePlacement.phase_id).where(
                TopicPhasePlacement.release_id == rid,
                TopicPhasePlacement.topic_id == topic.topic_id,
            )
        )
        results.append(_topic_summary(topic, list(track_ids), phase_id_for_topic))
    return ItemList[TopicSummary](items=results, next_cursor=next_cursor)


def topic_detail(session: Session, public_id: UUID, topic_id: str) -> TopicDetail:
    release = resolve_release(session, public_id)
    rid = release.id
    topic = require_topic(session, release, topic_id)
    track_ids = session.scalars(
        select(TopicTrackMembership.track_id)
        .where(TopicTrackMembership.release_id == rid, TopicTrackMembership.topic_id == topic_id)
        .order_by(TopicTrackMembership.track_id)
    ).all()
    phase_id = session.scalar(
        select(TopicPhasePlacement.phase_id).where(
            TopicPhasePlacement.release_id == rid, TopicPhasePlacement.topic_id == topic_id
        )
    )
    objectives = session.scalars(
        select(LearningObjective)
        .where(LearningObjective.release_id == rid, LearningObjective.topic_id == topic_id)
        .order_by(LearningObjective.ordinal)
    ).all()
    groups = session.scalars(
        select(PrerequisiteGroup)
        .where(PrerequisiteGroup.release_id == rid, PrerequisiteGroup.topic_id == topic_id)
        .order_by(PrerequisiteGroup.group_ordinal)
    ).all()
    group_responses = []
    for group in groups:
        members = session.scalars(
            select(PrerequisiteMember.prerequisite_topic_id)
            .where(
                PrerequisiteMember.release_id == rid,
                PrerequisiteMember.topic_id == topic_id,
                PrerequisiteMember.group_ordinal == group.group_ordinal,
            )
            .order_by(PrerequisiteMember.prerequisite_topic_id)
        ).all()
        group_responses.append(PrerequisiteGroupResponse(group_ordinal=group.group_ordinal, requires_all=list(members)))
    related = session.scalars(
        select(RelatedTopic.related_topic_id)
        .where(RelatedTopic.release_id == rid, RelatedTopic.topic_id == topic_id)
        .order_by(RelatedTopic.related_topic_id)
    ).all()

    result = TopicDetail(
        **_topic_summary(topic, list(track_ids), phase_id).model_dump(),
        pathway=topic.pathway,
        registry_status=topic.registry_status,
        dependency_review_status=topic.dependency_review_status,
        objectives=[
            ObjectiveResponse(
                type=objective.objective_type,
                text=objective.text,
                metadata=_metadata(objective.source_payload, {"type", "text"}),
            )
            for objective in objectives
        ],
        prerequisite_groups=group_responses,
        related_topic_ids=list(related),
    )
    return result


def curriculum_hierarchy(session: Session, public_id: UUID) -> CurriculumHierarchy:
    release = resolve_release(session, public_id)
    tracks = session.scalars(
        select(TrackVersion).where(TrackVersion.release_id == release.id).order_by(TrackVersion.track_id)
    ).all()
    phases = session.scalars(
        select(PhaseVersion).where(PhaseVersion.release_id == release.id).order_by(PhaseVersion.phase_id)
    ).all()
    return CurriculumHierarchy(
        release=_summary(release),
        tracks=[
            HierarchyTrack(
                track=_track(track),
                topic_ids=list(session.scalars(
                    select(TopicTrackMembership.topic_id)
                    .where(TopicTrackMembership.release_id == release.id, TopicTrackMembership.track_id == track.track_id)
                    .order_by(TopicTrackMembership.topic_id)
                ).all()),
            )
            for track in tracks
        ],
        phases=[
            HierarchyPhase(
                phase=_phase(phase),
                topic_ids=list(session.scalars(
                    select(TopicPhasePlacement.topic_id)
                    .where(TopicPhasePlacement.release_id == release.id, TopicPhasePlacement.phase_id == phase.phase_id)
                    .order_by(TopicPhasePlacement.topic_id)
                ).all()),
            )
            for phase in phases
        ],
    )
