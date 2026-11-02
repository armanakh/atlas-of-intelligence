"""Explicit response schemas for release-scoped curriculum reads."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import Field

from app.schemas.api_common import APIModel


class ReleaseSummary(APIModel):
    release_id: UUID
    curriculum_version: str
    schema_version: str
    status: str | None
    imported_at: datetime


class ReleaseDetail(ReleaseSummary):
    track_count: int
    phase_count: int
    topic_count: int


class TrackResponse(APIModel):
    id: str
    title: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class PhaseResponse(APIModel):
    id: str
    title: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ObjectiveResponse(APIModel):
    type: str | None
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class PrerequisiteGroupResponse(APIModel):
    group_ordinal: int
    logic_within_group: Literal["AND"] = "AND"
    requires_all: list[str]


class TopicSummary(APIModel):
    id: str
    title: str
    description: str | None = None
    track_ids: list[str]
    phase_id: str | None
    current_priority: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TopicDetail(TopicSummary):
    pathway: str | None = None
    registry_status: str | None = None
    dependency_review_status: str | None = None
    objectives: list[ObjectiveResponse]
    prerequisite_groups: list[PrerequisiteGroupResponse]
    related_topic_ids: list[str]


class HierarchyTrack(APIModel):
    track: TrackResponse
    topic_ids: list[str]


class HierarchyPhase(APIModel):
    phase: PhaseResponse
    topic_ids: list[str]


class CurriculumHierarchy(APIModel):
    release: ReleaseSummary
    tracks: list[HierarchyTrack]
    phases: list[HierarchyPhase]


class TopicDependencies(APIModel):
    topic_id: str
    prerequisite_groups: list[PrerequisiteGroupResponse]
    group_logic: Literal["OR"] = "OR"
    direct_dependent_ids: list[str]
    ancestor_ids: list[str]
    downstream_dependent_ids: list[str]
    related_topic_ids: list[str]


class GroupReadiness(APIModel):
    group_ordinal: int
    readiness: Literal["ready", "not_ready", "unknown"]
    satisfied_topic_ids: list[str]
    not_satisfied_topic_ids: list[str]
    unknown_topic_ids: list[str]


class ReadinessResponse(APIModel):
    topic_id: str
    readiness: Literal["ready", "not_ready", "unknown"]
    ready: bool | None
    has_satisfied_group: bool
    groups: list[GroupReadiness]
