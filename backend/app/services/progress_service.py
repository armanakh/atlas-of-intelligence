"""Transactional learner progress operations with before-state history."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import APIError
from app.db.models import (
    Learner,
    LearnerProgress,
    ProgressHistory,
    TopicVersion,
)
from app.schemas.api_common import ItemList
from app.schemas.learner_api import ProgressEnvelope, ProgressPatch, ProgressResponse
from app.services.release_resolver import require_topic, resolve_release


def _view(row: LearnerProgress) -> ProgressResponse:
    return ProgressResponse(
        topic_id=row.topic_id,
        progress_status=row.progress_status,
        confidence=row.confidence,
        progress_scope=row.progress_scope,
        notes=row.notes,
        updated_at=row.updated_at,
    )


def _learner(session: Session, learner_id: int) -> None:
    if session.get(Learner, learner_id) is None:
        raise APIError(404, "learner_not_found", f"Learner {learner_id} was not found")


def list_progress(
    session: Session,
    public_id: UUID,
    learner_id: int,
    *,
    progress_status: str | None = None,
) -> ItemList[ProgressResponse]:
    release = resolve_release(session, public_id)
    _learner(session, learner_id)
    statement = (
        select(LearnerProgress)
        .join(TopicVersion, TopicVersion.topic_id == LearnerProgress.topic_id)
        .where(TopicVersion.release_id == release.id, LearnerProgress.learner_id == learner_id)
    )
    if progress_status is not None:
        statement = statement.where(LearnerProgress.progress_status == progress_status)
    rows = session.scalars(statement.order_by(LearnerProgress.topic_id)).all()
    return ItemList[ProgressResponse](items=[_view(row) for row in rows], next_cursor=None)


def get_progress(session: Session, public_id: UUID, learner_id: int, topic_id: str) -> ProgressEnvelope:
    release = resolve_release(session, public_id)
    require_topic(session, release, topic_id)
    _learner(session, learner_id)
    row = session.get(LearnerProgress, (learner_id, topic_id))
    return ProgressEnvelope(progress=_view(row) if row is not None else None)


def _append_before_image(
    session: Session,
    *,
    learner_id: int,
    topic_id: str,
    release_id: int,
    row: LearnerProgress | None,
    operation: str,
    public_release_id: UUID,
) -> None:
    existed = row is not None
    session.add(
        ProgressHistory(
            learner_id=learner_id,
            topic_id=topic_id,
            event_type="api_before_change" if existed else "api_before_change_unassessed",
            progress_status=row.progress_status if row else None,
            confidence=row.confidence if row else None,
            progress_scope=row.progress_scope if row else None,
            notes=row.notes if row else None,
            source_release_id=release_id,
            occurred_at=datetime.now(timezone.utc),
            source_payload={
                "operation": operation,
                "record_existed": existed,
                "public_release_id": str(public_release_id),
                "previous_source_payload": row.source_payload if row else {},
            },
        )
    )


def patch_progress(
    session: Session,
    public_id: UUID,
    learner_id: int,
    topic_id: str,
    patch: ProgressPatch,
) -> ProgressEnvelope:
    fields: dict[str, Any] = patch.model_dump(exclude_unset=True)
    with session.begin():
        release = resolve_release(session, public_id)
        require_topic(session, release, topic_id)
        _learner(session, learner_id)
        row = session.get(LearnerProgress, (learner_id, topic_id))

        previous = {
            "progress_status": row.progress_status if row else None,
            "confidence": row.confidence if row else None,
            "progress_scope": row.progress_scope if row else None,
            "notes": row.notes if row else None,
        }
        updated = dict(previous)
        updated.update(fields)
        if updated["progress_status"] is None and updated["confidence"] is None:
            raise APIError(422, "assessment_required", "A progress row must have a status or confidence; use DELETE to clear it")
        if updated == previous:
            return ProgressEnvelope(progress=_view(row) if row is not None else None)

        _append_before_image(
            session,
            learner_id=learner_id,
            topic_id=topic_id,
            release_id=release.id,
            row=row,
            operation="patch",
            public_release_id=public_id,
        )
        if row is None:
            row = LearnerProgress(
                learner_id=learner_id,
                topic_id=topic_id,
                source_payload={},
                **updated,
            )
            session.add(row)
        else:
            for field, value in updated.items():
                setattr(row, field, value)
        row.updated_at = datetime.now(timezone.utc)
        session.flush()
        response = ProgressEnvelope(progress=_view(row))
    return response


def clear_progress(session: Session, public_id: UUID, learner_id: int, topic_id: str) -> None:
    with session.begin():
        release = resolve_release(session, public_id)
        require_topic(session, release, topic_id)
        _learner(session, learner_id)
        row = session.get(LearnerProgress, (learner_id, topic_id))
        if row is None:
            return
        _append_before_image(
            session,
            learner_id=learner_id,
            topic_id=topic_id,
            release_id=release.id,
            row=row,
            operation="clear",
            public_release_id=public_id,
        )
        session.delete(row)
        session.flush()
