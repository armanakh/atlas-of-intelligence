"""Forward-compatible Pydantic models for the curriculum import boundary.

Unknown fields are allowed and retained in ``model_extra``. Callers should use
``model_dump(exclude_unset=True)`` when they need to distinguish omitted
optional metadata from an explicitly supplied empty value.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class OpenPayload(BaseModel):
    model_config = ConfigDict(extra="allow")


class ObjectiveInput(OpenPayload):
    type: str | None = None
    text: str


class PrerequisiteGroupInput(OpenPayload):
    requires_all: list[str] = Field(min_length=1)


class TrackInput(OpenPayload):
    id: str
    title: str


class PhaseInput(OpenPayload):
    id: str
    title: str


class TopicInput(OpenPayload):
    id: str
    title: str
    track_ids: list[str]
    phase_id: str
    objectives: list[ObjectiveInput] | None = None
    prerequisite_groups: list[PrerequisiteGroupInput] | None = None
    related_topic_ids: list[str] | None = None
    exercise_ids: list[str] | None = None
    project_ids: list[str] | None = None
    learning_resource_ids: list[str] | None = None


class CurriculumImportInput(OpenPayload):
    curriculum_version: str
    schema_version: str
    tracks: list[TrackInput] = Field(default_factory=list)
    phases: list[PhaseInput] = Field(default_factory=list)
    topics: list[TopicInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_topic_ids(self) -> "CurriculumImportInput":
        ids = [topic.id for topic in self.topics]
        if len(ids) != len(set(ids)):
            raise ValueError("Topic IDs must be unique within a curriculum release")
        return self


class LearnerProgressInput(OpenPayload):
    topic_id: str
    progress_status: str | None = None
    confidence: int | None = Field(default=None, ge=1, le=5)
    progress_scope: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def has_explicit_assessment(self) -> "LearnerProgressInput":
        allowed = {"Not started", "Learning", "Practicing", "Solid", "Revisit"}
        if self.progress_status is not None and self.progress_status not in allowed:
            raise ValueError("progress_status is not a canonical status")
        if self.progress_status is None and self.confidence is None:
            raise ValueError("An explicit progress status or confidence is required")
        return self
