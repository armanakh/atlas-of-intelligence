"""Read-only prerequisite evaluation and dependency navigation.

Each engine is bound to one curriculum release and one learner. Curriculum
relationships come only from that release; learner progress is read by stable
Topic ID. Related Topics are intentionally exposed through a separate method.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    CurriculumRelease,
    Learner,
    LearnerProgress,
    PrerequisiteGroup,
    PrerequisiteMember,
    RelatedTopic,
    TopicVersion,
)


class Readiness(StrEnum):
    READY = "ready"
    NOT_READY = "not_ready"
    UNKNOWN = "unknown"


class InvalidDependencyStructureError(ValueError):
    """Stored dependency data violates the validated curriculum contract."""


@dataclass(frozen=True)
class PrerequisiteGroupEvaluation:
    group_ordinal: int
    readiness: Readiness
    satisfied_topics: tuple[str, ...]
    not_satisfied_topics: tuple[str, ...]
    unknown_topics: tuple[str, ...]


@dataclass(frozen=True)
class ReadinessEvaluation:
    topic_id: str
    readiness: Readiness
    groups: tuple[PrerequisiteGroupEvaluation, ...]

    @property
    def ready(self) -> bool | None:
        """Boolean readiness, or None when available evidence is inconclusive."""
        if self.readiness is Readiness.UNKNOWN:
            return None
        return self.readiness is Readiness.READY

    @property
    def has_satisfied_group(self) -> bool:
        return any(group.readiness is Readiness.READY for group in self.groups)


class DependencyEngine:
    """Read-only queries for a selected release and learner.

    Queries run under ``Session.no_autoflush`` so calling the engine cannot
    flush pending learner or curriculum edits from the caller's Session.
    Prerequisite truth is determined only by a stored progress status of
    ``Solid``; confidence is not read.
    """

    def __init__(self, session: Session, *, release_id: int, learner_id: int | None = None):
        self.session = session
        self.release_id = release_id
        self.learner_id = learner_id

    def _require_release_and_topic(self, topic_id: str) -> None:
        with self.session.no_autoflush:
            if self.session.get(CurriculumRelease, self.release_id) is None:
                raise LookupError(f"Curriculum release {self.release_id} does not exist")
            if self.session.get(TopicVersion, (self.release_id, topic_id)) is None:
                raise LookupError(f"Topic {topic_id!r} does not exist in release {self.release_id}")

    def _require_learner(self) -> None:
        if self.learner_id is None:
            raise ValueError("learner_id is required for readiness evaluation")
        with self.session.no_autoflush:
            if self.session.get(Learner, self.learner_id) is None:
                raise LookupError(f"Learner {self.learner_id} does not exist")

    def evaluate_readiness(self, topic_id: str) -> ReadinessEvaluation:
        """Evaluate prerequisite groups using three-valued readiness logic.

        Members within a group are ANDed. Groups are ORed. A group is
        ``not_ready`` as soon as a known non-Solid status is present, even if
        another member is unassessed; otherwise missing progress makes it
        ``unknown``. The overall result is ready if any group is ready,
        unknown if no group is ready and at least one group is unknown, and
        not_ready otherwise. No groups means ready.
        """
        self._require_release_and_topic(topic_id)
        self._require_learner()
        with self.session.no_autoflush:
            groups = self.session.scalars(
                select(PrerequisiteGroup)
                .where(
                    PrerequisiteGroup.release_id == self.release_id,
                    PrerequisiteGroup.topic_id == topic_id,
                )
                .order_by(PrerequisiteGroup.group_ordinal)
            ).all()
            member_rows = self.session.execute(
                select(PrerequisiteMember.group_ordinal, PrerequisiteMember.prerequisite_topic_id)
                .where(
                    PrerequisiteMember.release_id == self.release_id,
                    PrerequisiteMember.topic_id == topic_id,
                )
                .order_by(PrerequisiteMember.group_ordinal, PrerequisiteMember.prerequisite_topic_id)
            ).all()
            status_rows = self.session.execute(
                select(LearnerProgress.topic_id, LearnerProgress.progress_status).where(
                    LearnerProgress.learner_id == self.learner_id,
                    LearnerProgress.topic_id.in_([row.prerequisite_topic_id for row in member_rows]),
                )
            ).all() if member_rows else []

        status_by_topic = dict(status_rows)
        members_by_group: dict[int, list[str]] = {group.group_ordinal: [] for group in groups}
        for row in member_rows:
            members_by_group.setdefault(row.group_ordinal, []).append(row.prerequisite_topic_id)
        empty_groups = [ordinal for ordinal, members in members_by_group.items() if not members]
        if empty_groups:
            raise InvalidDependencyStructureError(
                f"Topic {topic_id!r} has prerequisite groups without members: {empty_groups}"
            )

        evaluations: list[PrerequisiteGroupEvaluation] = []
        for group in groups:
            satisfied: list[str] = []
            not_satisfied: list[str] = []
            unknown: list[str] = []
            for prerequisite_id in members_by_group.get(group.group_ordinal, []):
                if prerequisite_id not in status_by_topic or status_by_topic[prerequisite_id] is None:
                    unknown.append(prerequisite_id)
                elif status_by_topic[prerequisite_id] == "Solid":
                    satisfied.append(prerequisite_id)
                else:
                    not_satisfied.append(prerequisite_id)

            if not_satisfied:
                group_readiness = Readiness.NOT_READY
            elif unknown:
                group_readiness = Readiness.UNKNOWN
            else:
                group_readiness = Readiness.READY
            evaluations.append(
                PrerequisiteGroupEvaluation(
                    group_ordinal=group.group_ordinal,
                    readiness=group_readiness,
                    satisfied_topics=tuple(satisfied),
                    not_satisfied_topics=tuple(not_satisfied),
                    unknown_topics=tuple(unknown),
                )
            )

        if not evaluations or any(group.readiness is Readiness.READY for group in evaluations):
            readiness = Readiness.READY
        elif any(group.readiness is Readiness.UNKNOWN for group in evaluations):
            readiness = Readiness.UNKNOWN
        else:
            readiness = Readiness.NOT_READY
        return ReadinessEvaluation(topic_id, readiness, tuple(evaluations))

    def direct_prerequisite_groups(self, topic_id: str) -> tuple[tuple[int, tuple[str, ...]], ...]:
        """Return each stored OR group with its ordinal and AND members."""
        self._require_release_and_topic(topic_id)
        with self.session.no_autoflush:
            groups = self.session.scalars(
                select(PrerequisiteGroup.group_ordinal)
                .where(PrerequisiteGroup.release_id == self.release_id, PrerequisiteGroup.topic_id == topic_id)
                .order_by(PrerequisiteGroup.group_ordinal)
            ).all()
            rows = self.session.execute(
                select(PrerequisiteMember.group_ordinal, PrerequisiteMember.prerequisite_topic_id)
                .where(PrerequisiteMember.release_id == self.release_id, PrerequisiteMember.topic_id == topic_id)
                .order_by(PrerequisiteMember.group_ordinal, PrerequisiteMember.prerequisite_topic_id)
            ).all()
        by_ordinal: dict[int, list[str]] = {ordinal: [] for ordinal in groups}
        for ordinal, prerequisite_id in rows:
            by_ordinal.setdefault(ordinal, []).append(prerequisite_id)
        empty_groups = [ordinal for ordinal, members in by_ordinal.items() if not members]
        if empty_groups:
            raise InvalidDependencyStructureError(
                f"Topic {topic_id!r} has prerequisite groups without members: {empty_groups}"
            )
        return tuple((ordinal, tuple(by_ordinal[ordinal])) for ordinal in groups)

    def direct_prerequisites(self, topic_id: str) -> tuple[tuple[str, ...], ...]:
        """Return prerequisite groups; each inner tuple is one AND group."""
        return tuple(members for _, members in self.direct_prerequisite_groups(topic_id))

    def direct_dependents(self, topic_id: str) -> tuple[str, ...]:
        """Return Topics that directly list ``topic_id`` as a prerequisite."""
        self._require_release_and_topic(topic_id)
        with self.session.no_autoflush:
            return tuple(self.session.scalars(
                select(PrerequisiteMember.topic_id)
                .where(
                    PrerequisiteMember.release_id == self.release_id,
                    PrerequisiteMember.prerequisite_topic_id == topic_id,
                )
                .distinct()
                .order_by(PrerequisiteMember.topic_id)
            ).all())

    def prerequisite_ancestors(self, topic_id: str) -> tuple[str, ...]:
        """Return all transitively required Topics, with cycles safely bounded."""
        return self._walk(topic_id, reverse=False)

    def downstream_dependents(self, topic_id: str) -> tuple[str, ...]:
        """Return all transitive dependents, with cycles safely bounded."""
        return self._walk(topic_id, reverse=True)

    def related_topics(self, topic_id: str) -> tuple[str, ...]:
        """Return direct Related Topics, without combining them with graph edges."""
        self._require_release_and_topic(topic_id)
        with self.session.no_autoflush:
            return tuple(self.session.scalars(
                select(RelatedTopic.related_topic_id)
                .where(RelatedTopic.release_id == self.release_id, RelatedTopic.topic_id == topic_id)
                .order_by(RelatedTopic.related_topic_id)
            ).all())

    def _walk(self, topic_id: str, *, reverse: bool) -> tuple[str, ...]:
        self._require_release_and_topic(topic_id)
        visited = {topic_id}
        frontier = [topic_id]
        discovered: set[str] = set()
        with self.session.no_autoflush:
            while frontier:
                current = frontier.pop()
                if reverse:
                    neighbor_column = PrerequisiteMember.topic_id
                    statement = select(neighbor_column).where(
                        PrerequisiteMember.release_id == self.release_id,
                        PrerequisiteMember.prerequisite_topic_id == current,
                    )
                else:
                    neighbor_column = PrerequisiteMember.prerequisite_topic_id
                    statement = select(neighbor_column).where(
                        PrerequisiteMember.release_id == self.release_id,
                        PrerequisiteMember.topic_id == current,
                    )
                neighbors = self.session.scalars(statement.distinct().order_by(neighbor_column)).all()
                for neighbor in neighbors:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        discovered.add(neighbor)
                        frontier.append(neighbor)
        return tuple(sorted(discovered))
