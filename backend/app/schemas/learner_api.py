"""Explicit learner progress request and response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.schemas.api_common import APIModel


ProgressStatus = Literal["Not started", "Learning", "Practicing", "Solid", "Revisit"]


class ActiveReleaseSelection(APIModel):
    release_id: UUID


class LearnerResponse(APIModel):
    """Minimal public learner representation used for local learner resolution."""

    learner_id: int
    display_name: str | None


class ProgressResponse(APIModel):
    topic_id: str
    progress_status: ProgressStatus | None
    confidence: int | None = Field(default=None, ge=1, le=5)
    progress_scope: str | None
    notes: str | None
    updated_at: datetime


class ProgressEnvelope(APIModel):
    progress: ProgressResponse | None


class ProgressPatch(APIModel):
    progress_status: ProgressStatus | None = None
    confidence: int | None = Field(default=None, ge=1, le=5)
    progress_scope: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def require_some_field(self) -> "ProgressPatch":
        if not self.model_fields_set:
            raise ValueError("At least one field must be supplied")
        return self
