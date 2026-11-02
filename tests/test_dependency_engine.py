import os
from pathlib import Path
import zipfile

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.database import make_session_factory
from app.db.models import (
    CurriculumRelease,
    Learner,
    LearnerProgress,
    PrerequisiteGroup,
    PrerequisiteMember,
    RelatedTopic,
    TopicIdentity,
    TopicVersion,
)
from app.dependency import (
    DependencyEngine,
    InvalidDependencyStructureError,
    Readiness,
)
from app.importer import import_curriculum_package


PACKAGE_PATH = Path(os.environ.get(
    "ATLAS_TEST_CURRICULUM_PACKAGE",
    str(Path(__file__).resolve().parents[1] / "first_principles_ai_curriculum_v3_0_codex_clarified_package.zip"),
))
requires_curriculum_package = pytest.mark.skipif(
    not PACKAGE_PATH.is_file(),
    reason="Actual curriculum integration data is not bundled; set ATLAS_TEST_CURRICULUM_PACKAGE to a local package path.",
)


def make_graph(session, *, version="3.0.0", topic_ids=("T", "A", "B", "C", "D", "E", "R")):
    release = CurriculumRelease(
        curriculum_version=version,
        schema_version="1.0.0-draft",
        source_payload={},
        dependency_payload={},
    )
    learner = Learner(display_name="Fixture learner", source_payload={})
    session.add_all([release, learner])
    session.flush()
    for topic_id in topic_ids:
        session.add(TopicIdentity(topic_id=topic_id))
        session.flush()
        session.add(TopicVersion(release_id=release.id, topic_id=topic_id, title=topic_id, source_payload={}))
    session.flush()
    return release, learner


def add_group(session, release_id, topic_id, ordinal, members):
    session.add(PrerequisiteGroup(release_id=release_id, topic_id=topic_id, group_ordinal=ordinal, source_payload={}))
    session.flush()
    session.add_all(
        PrerequisiteMember(
            release_id=release_id,
            topic_id=topic_id,
            group_ordinal=ordinal,
            prerequisite_topic_id=member,
        )
        for member in members
    )


def progress(session, learner_id, topic_id, status=None, confidence=None):
    row = session.get(LearnerProgress, (learner_id, topic_id))
    if row is None:
        row = LearnerProgress(learner_id=learner_id, topic_id=topic_id)
        session.add(row)
    row.progress_status = status
    row.confidence = confidence


def test_no_prerequisites_are_ready_and_do_not_require_phase_placement(session):
    release, learner = make_graph(session)
    session.commit()
    result = DependencyEngine(session, release_id=release.id, learner_id=learner.id).evaluate_readiness("T")
    assert result.readiness is Readiness.READY
    assert result.ready is True
    assert result.groups == ()
    assert result.has_satisfied_group is False


@pytest.mark.parametrize(
    ("status", "confidence", "expected"),
    [
        ("Not started", 5, Readiness.NOT_READY),
        ("Learning", 5, Readiness.NOT_READY),
        ("Practicing", 5, Readiness.NOT_READY),
        ("Solid", 1, Readiness.READY),
        ("Revisit", 5, Readiness.NOT_READY),
    ],
)
def test_each_progress_status_and_confidence_independence(session, status, confidence, expected):
    release, learner = make_graph(session, topic_ids=("T", "A"))
    add_group(session, release.id, "T", 0, ["A"])
    progress(session, learner.id, "A", status, confidence)
    session.commit()
    result = DependencyEngine(session, release_id=release.id, learner_id=learner.id).evaluate_readiness("T")
    assert result.readiness is expected
    assert result.groups[0].satisfied_topics == (("A",) if status == "Solid" else ())
    assert result.groups[0].not_satisfied_topics == (() if status == "Solid" else ("A",))
    assert result.groups[0].unknown_topics == ()


def test_or_groups_and_and_members_preserve_partial_and_unknown_states(session):
    release, learner = make_graph(session, topic_ids=("T", "A", "B", "C"))
    add_group(session, release.id, "T", 0, ["A", "B"])
    add_group(session, release.id, "T", 1, ["C"])
    progress(session, learner.id, "A", "Solid", 1)
    progress(session, learner.id, "B", "Learning", 5)
    session.commit()

    engine = DependencyEngine(session, release_id=release.id, learner_id=learner.id)
    result = engine.evaluate_readiness("T")
    assert engine.direct_prerequisites("T") == (("A", "B"), ("C",))
    assert result.readiness is Readiness.UNKNOWN
    assert result.groups[0].readiness is Readiness.NOT_READY
    assert result.groups[0].satisfied_topics == ("A",)
    assert result.groups[0].not_satisfied_topics == ("B",)
    assert result.groups[0].unknown_topics == ()
    assert result.groups[1].readiness is Readiness.UNKNOWN
    assert result.groups[1].unknown_topics == ("C",)
    assert result.ready is None
    assert result.has_satisfied_group is False
    assert session.get(LearnerProgress, (learner.id, "C")) is None

    progress(session, learner.id, "C", "Solid", 2)
    session.commit()
    result = engine.evaluate_readiness("T")
    assert result.readiness is Readiness.READY  # OR: group 1 is complete.
    assert result.has_satisfied_group is True

    progress(session, learner.id, "B", "Solid", 1)
    session.commit()
    result = engine.evaluate_readiness("T")
    assert result.groups[0].readiness is Readiness.READY  # AND: both members Solid.


def test_missing_progress_is_unknown_and_confidence_only_does_not_satisfy(session):
    release, learner = make_graph(session, topic_ids=("T", "A", "B"))
    add_group(session, release.id, "T", 0, ["A", "B"])
    progress(session, learner.id, "A", confidence=5)
    session.commit()
    result = DependencyEngine(session, release_id=release.id, learner_id=learner.id).evaluate_readiness("T")
    assert result.readiness is Readiness.UNKNOWN
    assert result.groups[0].unknown_topics == ("A", "B")
    assert session.get(LearnerProgress, (learner.id, "B")) is None


def test_direct_transitive_navigation_and_related_topics_are_separate(session):
    release, learner = make_graph(session)
    add_group(session, release.id, "T", 0, ["A", "B"])
    add_group(session, release.id, "T", 1, ["C"])
    add_group(session, release.id, "D", 0, ["T"])
    add_group(session, release.id, "E", 0, ["D"])
    session.add(RelatedTopic(release_id=release.id, topic_id="T", related_topic_id="R"))
    session.commit()

    engine = DependencyEngine(session, release_id=release.id, learner_id=learner.id)
    assert engine.direct_prerequisites("T") == (("A", "B"), ("C",))
    assert engine.direct_dependents("T") == ("D",)
    assert engine.prerequisite_ancestors("E") == ("A", "B", "C", "D", "T")
    assert engine.downstream_dependents("A") == ("D", "E", "T")
    assert engine.related_topics("T") == ("R",)
    assert "R" not in engine.prerequisite_ancestors("T")
    assert "R" not in engine.downstream_dependents("A")


def test_cycle_in_invalid_stored_graph_does_not_loop_or_return_start(session):
    release, learner = make_graph(session, topic_ids=("A", "B", "C"))
    add_group(session, release.id, "A", 0, ["B"])
    add_group(session, release.id, "B", 0, ["C"])
    add_group(session, release.id, "C", 0, ["A"])
    session.commit()
    engine = DependencyEngine(session, release_id=release.id, learner_id=learner.id)
    assert engine.prerequisite_ancestors("A") == ("B", "C")
    assert engine.downstream_dependents("A") == ("B", "C")


def test_empty_prerequisite_group_is_rejected_as_invalid_contract(session):
    release, learner = make_graph(session, topic_ids=("T",))
    session.add(PrerequisiteGroup(release_id=release.id, topic_id="T", group_ordinal=0, source_payload={}))
    session.commit()
    engine = DependencyEngine(session, release_id=release.id, learner_id=learner.id)
    with pytest.raises(InvalidDependencyStructureError, match="without members"):
        engine.evaluate_readiness("T")


def test_engine_is_release_scoped_and_does_not_mutate_learner_data(session):
    release_a, learner = make_graph(session, version="3.0.0", topic_ids=("T", "A"))
    add_group(session, release_a.id, "T", 0, ["A"])
    release_b = CurriculumRelease(
        curriculum_version="3.1.0", schema_version="1.0.0-draft", source_payload={}, dependency_payload={}
    )
    session.add(release_b)
    session.flush()
    session.add_all(
        [
            TopicVersion(release_id=release_b.id, topic_id="T", title="T new", source_payload={}),
            TopicVersion(release_id=release_b.id, topic_id="A", title="A new", source_payload={}),
        ]
    )
    progress(session, learner.id, "A", "Solid", 3)
    session.commit()
    before = session.scalar(select(func.count()).select_from(LearnerProgress))
    engine_a = DependencyEngine(session, release_id=release_a.id, learner_id=learner.id)
    engine_b = DependencyEngine(session, release_id=release_b.id, learner_id=learner.id)
    assert engine_a.evaluate_readiness("T").readiness is Readiness.READY
    assert engine_b.evaluate_readiness("T").readiness is Readiness.READY
    assert engine_b.direct_prerequisites("T") == ()
    assert session.scalar(select(func.count()).select_from(LearnerProgress)) == before
    assert session.get(LearnerProgress, (learner.id, "A")).progress_status == "Solid"
    assert session.get(LearnerProgress, (learner.id, "T")) is None


def test_engine_does_not_autoflush_callers_pending_learner_changes(session):
    release, learner = make_graph(session, topic_ids=("T", "A"))
    add_group(session, release.id, "T", 0, ["A"])
    session.commit()
    release_id, learner_id = release.id, learner.id
    pending = LearnerProgress(learner_id=learner_id, topic_id="A", progress_status="Solid")
    session.add(pending)

    result = DependencyEngine(session, release_id=release_id, learner_id=learner_id).evaluate_readiness("T")
    assert result.readiness is Readiness.UNKNOWN  # Pending caller work is not flushed by a read query.
    assert pending in session.new
    with Session(session.get_bind()) as independent_session:
        assert independent_session.get(LearnerProgress, (learner_id, "A")) is None


@requires_curriculum_package
def test_unassessed_actual_curriculum_topic_and_related_link_integration(engine):
    package_path = PACKAGE_PATH
    factory = make_session_factory(engine)
    imported = import_curriculum_package(package_path, factory)
    with Session(engine) as session:
        learner = session.scalar(select(Learner))
        topic_with_related = session.scalar(
            select(RelatedTopic.topic_id).where(RelatedTopic.release_id == imported.release_id)
        )
        related_id = session.scalar(
            select(RelatedTopic.related_topic_id).where(
                RelatedTopic.release_id == imported.release_id,
                RelatedTopic.topic_id == topic_with_related,
            )
        )
        engine_api = DependencyEngine(session, release_id=imported.release_id, learner_id=learner.id)
        assert related_id in engine_api.related_topics(topic_with_related)
        assert related_id not in {
            member
            for group in engine_api.direct_prerequisites(topic_with_related)
            for member in group
        }

        unassessed_id = session.scalar(
            select(TopicVersion.topic_id)
            .where(TopicVersion.release_id == imported.release_id)
            .where(~TopicVersion.topic_id.in_(select(LearnerProgress.topic_id).where(LearnerProgress.learner_id == learner.id)))
            .order_by(TopicVersion.topic_id)
        )
        assert unassessed_id is not None
        assert session.get(LearnerProgress, (learner.id, unassessed_id)) is None
        before_progress = session.scalar(
            select(func.count()).select_from(LearnerProgress).where(LearnerProgress.learner_id == learner.id)
        )
        engine_api.evaluate_readiness(unassessed_id)
        assert session.scalar(
            select(func.count()).select_from(LearnerProgress).where(LearnerProgress.learner_id == learner.id)
        ) == before_progress
