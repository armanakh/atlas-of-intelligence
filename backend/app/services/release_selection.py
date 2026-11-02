"""Explicit singleton active-release selection."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.api.errors import APIError
from app.db.models import ActiveCurriculumRelease, CurriculumRelease
from app.schemas.curriculum_api import ReleaseSummary
from app.services.release_resolver import resolve_release


def _summary(release: CurriculumRelease) -> ReleaseSummary:
    return ReleaseSummary(
        release_id=UUID(release.public_id),
        curriculum_version=release.curriculum_version,
        schema_version=release.schema_version,
        status=release.release_status,
        imported_at=release.imported_at,
    )


def get_active_release(session: Session) -> ReleaseSummary:
    pointer = session.get(ActiveCurriculumRelease, 1)
    if pointer is None:
        raise APIError(409, "active_release_not_selected", "No active curriculum release has been selected")
    release = session.get(CurriculumRelease, pointer.release_id)
    if release is None:  # Defends against a manually corrupted database; FK enforcement should prevent this.
        raise APIError(500, "active_release_integrity_error", "The active release pointer is invalid")
    return _summary(release)


def select_active_release(session: Session, public_id: UUID) -> ReleaseSummary:
    with session.begin():
        release = resolve_release(session, public_id)
        report = release.source_payload.get("validation_report", {})
        maturity = report.get("content_maturity", {}) if isinstance(report, dict) else {}
        if maturity.get("structural_validation") != "passed":
            raise APIError(409, "release_not_validated", "The release has not passed structural validation")

        pointer = session.get(ActiveCurriculumRelease, 1)
        if pointer is None:
            pointer = ActiveCurriculumRelease(singleton_id=1, release_id=release.id)
            session.add(pointer)
        else:
            pointer.release_id = release.id
        session.flush()
        return _summary(release)
