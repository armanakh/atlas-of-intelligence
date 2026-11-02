"""Adapters from the dependency engine's domain results to API views."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.api.errors import APIError
from app.db.models import Learner
from app.dependency import DependencyEngine
from app.schemas.curriculum_api import (
    GroupReadiness,
    ReadinessResponse,
    TopicDependencies,
    PrerequisiteGroupResponse,
)
from app.services.release_resolver import require_topic, resolve_release


def _require_learner(session: Session, learner_id: int) -> None:
    if session.get(Learner, learner_id) is None:
        raise APIError(404, "learner_not_found", f"Learner {learner_id} was not found")


def readiness(session: Session, public_id: UUID, learner_id: int, topic_id: str) -> ReadinessResponse:
    release = resolve_release(session, public_id)
    require_topic(session, release, topic_id)
    _require_learner(session, learner_id)
    result = DependencyEngine(session, release_id=release.id, learner_id=learner_id).evaluate_readiness(topic_id)
    return ReadinessResponse(
        topic_id=result.topic_id,
        readiness=result.readiness.value,
        ready=result.ready,
        has_satisfied_group=result.has_satisfied_group,
        groups=[
            GroupReadiness(
                group_ordinal=group.group_ordinal,
                readiness=group.readiness.value,
                satisfied_topic_ids=list(group.satisfied_topics),
                not_satisfied_topic_ids=list(group.not_satisfied_topics),
                unknown_topic_ids=list(group.unknown_topics),
            )
            for group in result.groups
        ],
    )


def topic_dependencies(session: Session, public_id: UUID, topic_id: str) -> TopicDependencies:
    release = resolve_release(session, public_id)
    require_topic(session, release, topic_id)
    engine = DependencyEngine(session, release_id=release.id)
    groups = engine.direct_prerequisite_groups(topic_id)
    return TopicDependencies(
        topic_id=topic_id,
        prerequisite_groups=[
            PrerequisiteGroupResponse(group_ordinal=ordinal, requires_all=list(members))
            for ordinal, members in groups
        ],
        direct_dependent_ids=list(engine.direct_dependents(topic_id)),
        ancestor_ids=list(engine.prerequisite_ancestors(topic_id)),
        downstream_dependent_ids=list(engine.downstream_dependents(topic_id)),
        related_topic_ids=list(engine.related_topics(topic_id)),
    )
