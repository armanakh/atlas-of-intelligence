from pathlib import Path

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError

from app.db.models import (
    Base,
    CurriculumRelease,
    Learner,
    LearnerProgress,
    PhaseVersion,
    PrerequisiteGroup,
    PrerequisiteMember,
    RelatedTopic,
    TopicIdentity,
    TopicPhasePlacement,
    TopicTrackMembership,
    TopicVersion,
    TrackVersion,
)


def add_release(session, version="3.0.0", schema="1.0.0-draft"):
    release = CurriculumRelease(curriculum_version=version, schema_version=schema)
    session.add(release)
    session.flush()
    return release


def add_topic(session, release_id, topic_id, **payload):
    session.add(TopicIdentity(topic_id=topic_id))
    session.flush()
    session.add(
        TopicVersion(
            release_id=release_id,
            topic_id=topic_id,
            title=payload.get("title", topic_id),
            source_payload=payload or {},
        )
    )
    session.flush()


def test_database_creation_and_sqlite_foreign_key_enforcement(engine):
    names = set(inspect(engine).get_table_names())
    assert "curriculum_release" in names
    assert "topic_version" in names
    assert "learner_progress" in names
    with engine.connect() as connection:
        assert connection.scalar(text("PRAGMA foreign_keys")) == 1


def test_foreign_key_rejects_missing_track_or_topic(session):
    release = add_release(session)
    session.add(TopicTrackMembership(release_id=release.id, topic_id="NO-TOPIC", track_id="NO-TRACK"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_topic_ids_are_unique_within_release_and_reusable_across_releases(session):
    first = add_release(session)
    add_topic(session, first.id, "ML-001")
    session.commit()
    learner = Learner(display_name="Local learner")
    session.add(learner)
    session.flush()
    session.add(LearnerProgress(learner_id=learner.id, topic_id="ML-001", progress_status="Practicing"))
    session.commit()

    session.add(
        TopicVersion(release_id=first.id, topic_id="ML-001", title="duplicate snapshot topic")
    )
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()

    # A second release can snapshot the same durable identity.
    second = add_release(session, version="3.1.0")
    session.add(TopicVersion(release_id=second.id, topic_id="ML-001", title="renamed in new release"))
    session.commit()
    assert session.scalar(select(TopicVersion).where(TopicVersion.release_id == second.id)).title == "renamed in new release"
    assert session.get(LearnerProgress, (learner.id, "ML-001")).progress_status == "Practicing"


def test_track_membership_and_phase_placement_are_separate(session):
    release = add_release(session)
    add_topic(session, release.id, "CS-001")
    session.add_all(
        [
            TrackVersion(release_id=release.id, track_id="TR-CS", title="Computer Science"),
            TrackVersion(release_id=release.id, track_id="TR-MATH", title="Mathematics"),
            PhaseVersion(release_id=release.id, phase_id="PH01", title="Programming"),
        ]
    )
    session.flush()
    session.add_all(
        [
            TopicTrackMembership(release_id=release.id, topic_id="CS-001", track_id="TR-CS"),
            TopicTrackMembership(release_id=release.id, topic_id="CS-001", track_id="TR-MATH"),
            TopicPhasePlacement(release_id=release.id, topic_id="CS-001", phase_id="PH01"),
        ]
    )
    session.commit()
    assert session.scalar(select(TopicTrackMembership).where(TopicTrackMembership.track_id == "TR-MATH"))
    assert session.scalar(select(TopicPhasePlacement).where(TopicPhasePlacement.topic_id == "CS-001")).phase_id == "PH01"


def test_prerequisite_groups_and_members_preserve_or_and_structure(session):
    release = add_release(session)
    for topic_id in ("TOPIC", "A", "B", "C"):
        add_topic(session, release.id, topic_id)
    session.add_all(
        [
            PrerequisiteGroup(release_id=release.id, topic_id="TOPIC", group_ordinal=0),
            PrerequisiteGroup(release_id=release.id, topic_id="TOPIC", group_ordinal=1),
        ]
    )
    session.add_all(
        [
            PrerequisiteMember(release_id=release.id, topic_id="TOPIC", group_ordinal=0, prerequisite_topic_id="A"),
            PrerequisiteMember(release_id=release.id, topic_id="TOPIC", group_ordinal=0, prerequisite_topic_id="B"),
            PrerequisiteMember(release_id=release.id, topic_id="TOPIC", group_ordinal=1, prerequisite_topic_id="C"),
        ]
    )
    session.commit()
    groups = session.scalars(
        select(PrerequisiteGroup).where(PrerequisiteGroup.topic_id == "TOPIC").order_by(PrerequisiteGroup.group_ordinal)
    ).all()
    members_by_group = {
        group.group_ordinal: session.scalars(
            select(PrerequisiteMember.prerequisite_topic_id).where(
                PrerequisiteMember.topic_id == "TOPIC",
                PrerequisiteMember.group_ordinal == group.group_ordinal,
            )
        ).all()
        for group in groups
    }
    assert members_by_group == {0: ["A", "B"], 1: ["C"]}


def test_related_topics_have_separate_rows_and_do_not_become_prerequisites(session):
    release = add_release(session)
    for topic_id in ("A", "B"):
        add_topic(session, release.id, topic_id)
    session.add(RelatedTopic(release_id=release.id, topic_id="A", related_topic_id="B"))
    session.commit()
    assert session.scalar(select(RelatedTopic).where(RelatedTopic.topic_id == "A"))
    assert session.scalars(select(PrerequisiteMember)).all() == []


def test_progress_and_confidence_are_independent_and_absence_stays_absence(session):
    release = add_release(session)
    add_topic(session, release.id, "STATUS-ONLY")
    add_topic(session, release.id, "CONFIDENCE-ONLY")
    learner = Learner(display_name="Local learner")
    session.add(learner)
    session.flush()
    session.add_all(
        [
            LearnerProgress(learner_id=learner.id, topic_id="STATUS-ONLY", progress_status="Learning"),
            LearnerProgress(learner_id=learner.id, topic_id="CONFIDENCE-ONLY", confidence=4),
        ]
    )
    session.commit()
    status_only = session.get(LearnerProgress, (learner.id, "STATUS-ONLY"))
    confidence_only = session.get(LearnerProgress, (learner.id, "CONFIDENCE-ONLY"))
    assert status_only.progress_status == "Learning" and status_only.confidence is None
    assert confidence_only.progress_status is None and confidence_only.confidence == 4
    assert session.get(LearnerProgress, (learner.id, "UNASSESSED")) is None


def test_curriculum_metadata_payload_round_trips_without_simplification(session):
    release = add_release(session)
    metadata = {
        "learning_target": "Understand the mechanism",
        "depth_frontier": ["defer advanced proof"],
        "exercise_ids": [],
        "future_unknown_field": {"keep": True, "labels": ["x", "y"]},
    }
    add_topic(session, release.id, "META-001", **metadata)
    session.commit()
    topic = session.get(TopicVersion, (release.id, "META-001"))
    assert topic.source_payload == metadata


def test_learner_history_and_evidence_are_persisted_separately(session):
    from app.db.models import LearnerEvidence, ProgressHistory, ProgressHistoryEvidence

    release = add_release(session)
    add_topic(session, release.id, "CS-001")
    learner = Learner(display_name="Local learner")
    session.add(learner)
    session.flush()
    evidence = LearnerEvidence(
        learner_id=learner.id,
        evidence_id="EV-1",
        evidence_type="implementation",
        description="Built a small example",
        source_payload={"source": "local note", "unknown": [1, 2]},
    )
    event = ProgressHistory(
        learner_id=learner.id,
        topic_id="CS-001",
        event_type="assessment",
        progress_status="Practicing",
        confidence=None,
        source_release_id=release.id,
    )
    session.add_all([evidence, event])
    session.flush()
    session.add(
        ProgressHistoryEvidence(
            history_id=event.id,
            learner_id=learner.id,
            topic_id="CS-001",
            evidence_id="EV-1",
        )
    )
    session.commit()
    assert session.get(LearnerEvidence, (learner.id, "EV-1")).source_payload["unknown"] == [1, 2]
    assert session.scalar(select(ProgressHistory).where(ProgressHistory.topic_id == "CS-001")).progress_status == "Practicing"


def test_alembic_initial_migration_executes_and_is_idempotent(tmp_path: Path):
    from app.db.initialize import initialize_database

    db_path = tmp_path / "migrated.db"
    url = f"sqlite:///{db_path}"
    initialize_database(url)
    initialize_database(url)
    from app.db.database import make_engine

    migrated_engine = make_engine(url)
    try:
        names = set(inspect(migrated_engine).get_table_names())
        assert "alembic_version" in names
        assert "curriculum_release" in names
        assert "progress_history_evidence" in names
        for table_name, table in Base.metadata.tables.items():
            migrated_columns = {column["name"] for column in inspect(migrated_engine).get_columns(table_name)}
            assert migrated_columns == set(table.columns.keys())
    finally:
        migrated_engine.dispose()
