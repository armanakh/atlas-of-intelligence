"""Resolve public curriculum release UUIDs without leaking internal keys."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import APIError
from app.db.models import CurriculumRelease, TopicVersion


def resolve_release(session: Session, public_id: UUID) -> CurriculumRelease:
    release = session.scalar(select(CurriculumRelease).where(CurriculumRelease.public_id == str(public_id)))
    if release is None:
        raise APIError(404, "release_not_found", f"Release {public_id} was not found")
    return release


def require_topic(session: Session, release: CurriculumRelease, topic_id: str) -> TopicVersion:
    topic = session.get(TopicVersion, (release.id, topic_id))
    if topic is None:
        raise APIError(404, "topic_not_found", f"Topic {topic_id!r} is not in this release")
    return topic
