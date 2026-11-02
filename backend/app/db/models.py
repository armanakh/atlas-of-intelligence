"""SQLAlchemy models for curriculum snapshots and learner-owned state."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base metadata shared by application models and Alembic."""


class CurriculumRelease(Base):
    __tablename__ = "curriculum_release"
    __table_args__ = (
        UniqueConstraint(
            "curriculum_version", "schema_version", "source_digest",
            name="uq_curriculum_release_version_schema_digest",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, default=lambda: str(uuid4()))
    curriculum_version: Mapped[str] = mapped_column(String(100), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(100), nullable=False)
    release_status: Mapped[str | None] = mapped_column(String(100))
    source_digest: Mapped[str | None] = mapped_column(String(128))
    source_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    dependency_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )


class ActiveCurriculumRelease(Base):
    """Zero-or-one explicitly selected release; status is not selection."""

    __tablename__ = "active_curriculum_release"
    __table_args__ = (
        CheckConstraint("singleton_id = 1", name="ck_active_curriculum_release_singleton"),
        UniqueConstraint("release_id", name="uq_active_curriculum_release_release_id"),
    )

    singleton_id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    release_id: Mapped[int] = mapped_column(
        ForeignKey("curriculum_release.id", ondelete="RESTRICT"), nullable=False
    )


class TrackVersion(Base):
    __tablename__ = "track_version"

    release_id: Mapped[int] = mapped_column(ForeignKey("curriculum_release.id", ondelete="CASCADE"), primary_key=True)
    track_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class PhaseVersion(Base):
    __tablename__ = "phase_version"

    release_id: Mapped[int] = mapped_column(ForeignKey("curriculum_release.id", ondelete="CASCADE"), primary_key=True)
    phase_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class TopicIdentity(Base):
    """Release-independent durable Topic ID referenced by learner state."""

    __tablename__ = "topic_identity"

    topic_id: Mapped[str] = mapped_column(String(100), primary_key=True)


class TopicVersion(Base):
    __tablename__ = "topic_version"
    __table_args__ = (
        ForeignKeyConstraint(["release_id"], ["curriculum_release.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["topic_id"], ["topic_identity.topic_id"]),
    )

    release_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    pathway: Mapped[str | None] = mapped_column(String(100))
    current_priority: Mapped[str | None] = mapped_column(String(100))
    registry_status: Mapped[str | None] = mapped_column(String(100))
    dependency_review_status: Mapped[str | None] = mapped_column(String(100))
    source_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class TopicPhasePlacement(Base):
    """Current roadmap placement, stored independently from Topic identity."""

    __tablename__ = "topic_phase_placement"
    __table_args__ = (
        ForeignKeyConstraint(["release_id", "topic_id"], ["topic_version.release_id", "topic_version.topic_id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["release_id", "phase_id"], ["phase_version.release_id", "phase_version.phase_id"]),
    )

    release_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    phase_id: Mapped[str] = mapped_column(String(100), nullable=False)


class TopicTrackMembership(Base):
    __tablename__ = "topic_track_membership"
    __table_args__ = (
        ForeignKeyConstraint(["release_id", "topic_id"], ["topic_version.release_id", "topic_version.topic_id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["release_id", "track_id"], ["track_version.release_id", "track_version.track_id"]),
    )

    release_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    track_id: Mapped[str] = mapped_column(String(100), primary_key=True)


class LearningObjective(Base):
    __tablename__ = "learning_objective"
    __table_args__ = (
        ForeignKeyConstraint(["release_id", "topic_id"], ["topic_version.release_id", "topic_version.topic_id"], ondelete="CASCADE"),
    )

    release_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    ordinal: Mapped[int] = mapped_column(Integer, primary_key=True)
    objective_type: Mapped[str | None] = mapped_column(String(100))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    source_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class PrerequisiteGroup(Base):
    """One OR alternative; its members are ANDed together."""

    __tablename__ = "prerequisite_group"
    __table_args__ = (
        ForeignKeyConstraint(["release_id", "topic_id"], ["topic_version.release_id", "topic_version.topic_id"], ondelete="CASCADE"),
    )

    release_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    group_ordinal: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class PrerequisiteMember(Base):
    __tablename__ = "prerequisite_member"
    __table_args__ = (
        ForeignKeyConstraint(
            ["release_id", "topic_id", "group_ordinal"],
            ["prerequisite_group.release_id", "prerequisite_group.topic_id", "prerequisite_group.group_ordinal"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(["release_id", "prerequisite_topic_id"], ["topic_version.release_id", "topic_version.topic_id"]),
        CheckConstraint("topic_id <> prerequisite_topic_id", name="ck_prerequisite_not_self"),
    )

    release_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    group_ordinal: Mapped[int] = mapped_column(Integer, primary_key=True)
    prerequisite_topic_id: Mapped[str] = mapped_column(String(100), primary_key=True)


class RelatedTopic(Base):
    __tablename__ = "related_topic"
    __table_args__ = (
        ForeignKeyConstraint(["release_id", "topic_id"], ["topic_version.release_id", "topic_version.topic_id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["release_id", "related_topic_id"], ["topic_version.release_id", "topic_version.topic_id"]),
        CheckConstraint("topic_id <> related_topic_id", name="ck_related_topic_not_self"),
    )

    release_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    related_topic_id: Mapped[str] = mapped_column(String(100), primary_key=True)


class CurriculumItem(Base):
    """Extensible entity slot for future exercise, project, or resource records."""

    __tablename__ = "curriculum_item"
    __table_args__ = (
        CheckConstraint("item_kind IN ('exercise', 'project', 'learning_resource')", name="ck_curriculum_item_kind"),
    )

    release_id: Mapped[int] = mapped_column(ForeignKey("curriculum_release.id", ondelete="CASCADE"), primary_key=True)
    item_kind: Mapped[str] = mapped_column(String(40), primary_key=True)
    item_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    title: Mapped[str | None] = mapped_column(String(500))
    source_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class TopicCurriculumItem(Base):
    __tablename__ = "topic_curriculum_item"
    __table_args__ = (
        ForeignKeyConstraint(["release_id", "topic_id"], ["topic_version.release_id", "topic_version.topic_id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["release_id", "item_kind", "item_id"], ["curriculum_item.release_id", "curriculum_item.item_kind", "curriculum_item.item_id"]),
    )

    release_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    item_kind: Mapped[str] = mapped_column(String(40), primary_key=True)
    item_id: Mapped[str] = mapped_column(String(100), primary_key=True)


class CurriculumMigration(Base):
    __tablename__ = "curriculum_migration"
    __table_args__ = (
        ForeignKeyConstraint(["release_id"], ["curriculum_release.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["retired_topic_id"], ["topic_identity.topic_id"]),
    )

    release_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    retired_topic_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    disposition: Mapped[str] = mapped_column(String(100), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    source_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CurriculumMigrationDestination(Base):
    __tablename__ = "curriculum_migration_destination"
    __table_args__ = (
        ForeignKeyConstraint(
            ["release_id", "retired_topic_id"],
            ["curriculum_migration.release_id", "curriculum_migration.retired_topic_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(["release_id", "destination_topic_id"], ["topic_version.release_id", "topic_version.topic_id"]),
    )

    release_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    retired_topic_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    destination_topic_id: Mapped[str] = mapped_column(String(100), primary_key=True)


class Learner(Base):
    __tablename__ = "learner"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    display_name: Mapped[str | None] = mapped_column(String(200))
    source_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.current_timestamp())


class LearnerProgress(Base):
    """Only explicit assessments create rows; either field may be independently absent."""

    __tablename__ = "learner_progress"
    __table_args__ = (
        ForeignKeyConstraint(["topic_id"], ["topic_identity.topic_id"]),
        CheckConstraint(
            "progress_status IS NOT NULL OR confidence IS NOT NULL",
            name="ck_progress_has_assessed_field",
        ),
        CheckConstraint(
            "progress_status IS NULL OR progress_status IN ('Not started', 'Learning', 'Practicing', 'Solid', 'Revisit')",
            name="ck_progress_status",
        ),
        CheckConstraint("confidence IS NULL OR confidence BETWEEN 1 AND 5", name="ck_progress_confidence"),
    )

    learner_id: Mapped[int] = mapped_column(ForeignKey("learner.id", ondelete="CASCADE"), primary_key=True)
    topic_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    progress_status: Mapped[str | None] = mapped_column(String(30))
    confidence: Mapped[int | None] = mapped_column(Integer)
    progress_scope: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)
    source_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.current_timestamp())


class LearnerEvidence(Base):
    __tablename__ = "learner_evidence"

    learner_id: Mapped[int] = mapped_column(ForeignKey("learner.id", ondelete="CASCADE"), primary_key=True)
    evidence_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    evidence_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class ProgressHistory(Base):
    """An explicit state snapshot/event; it does not imply topic mastery."""

    __tablename__ = "progress_history"
    __table_args__ = (
        ForeignKeyConstraint(["learner_id"], ["learner.id",], ondelete="CASCADE"),
        ForeignKeyConstraint(["topic_id"], ["topic_identity.topic_id"]),
        ForeignKeyConstraint(["source_release_id"], ["curriculum_release.id"]),
        CheckConstraint(
            "progress_status IS NULL OR progress_status IN ('Not started', 'Learning', 'Practicing', 'Solid', 'Revisit')",
            name="ck_progress_history_status",
        ),
        CheckConstraint("confidence IS NULL OR confidence BETWEEN 1 AND 5", name="ck_progress_history_confidence"),
        UniqueConstraint("id", "learner_id", "topic_id", name="uq_progress_history_ref"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    learner_id: Mapped[int] = mapped_column(Integer, nullable=False)
    topic_id: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    progress_status: Mapped[str | None] = mapped_column(String(30))
    confidence: Mapped[int | None] = mapped_column(Integer)
    progress_scope: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)
    source_release_id: Mapped[int | None] = mapped_column(Integer)
    source_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.current_timestamp())


class ProgressHistoryEvidence(Base):
    __tablename__ = "progress_history_evidence"
    __table_args__ = (
        ForeignKeyConstraint(
            ["history_id", "learner_id", "topic_id"],
            ["progress_history.id", "progress_history.learner_id", "progress_history.topic_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(["learner_id", "evidence_id"], ["learner_evidence.learner_id", "learner_evidence.evidence_id"]),
    )

    history_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    learner_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    evidence_id: Mapped[str] = mapped_column(String(100), primary_key=True)
