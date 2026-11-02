import os
import json
import zipfile
from pathlib import Path

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.database import make_session_factory
from app.db.models import (
    Base,
    CurriculumMigration,
    CurriculumRelease,
    Learner,
    LearnerEvidence,
    LearnerProgress,
    LearningObjective,
    PhaseVersion,
    PrerequisiteGroup,
    PrerequisiteMember,
    ProgressHistory,
    RelatedTopic,
    TopicIdentity,
    TopicPhasePlacement,
    TopicTrackMembership,
    TopicVersion,
    TrackVersion,
)
from app.importer import (
    DuplicateReleaseError,
    LearnerStateConflictError,
    PackageValidationError,
    RetiredTopicIDReuseError,
    import_curriculum_package,
    main,
    validate_package,
)


PACKAGE_PATH = Path(os.environ.get(
    "ATLAS_TEST_CURRICULUM_PACKAGE",
    str(Path(__file__).resolve().parents[1] / "first_principles_ai_curriculum_v3_0_codex_clarified_package.zip"),
))
requires_curriculum_package = pytest.mark.skipif(
    not PACKAGE_PATH.is_file(),
    reason="Actual curriculum integration data is not bundled; set ATLAS_TEST_CURRICULUM_PACKAGE to a local package path.",
)


def package_files() -> dict[str, bytes]:
    with zipfile.ZipFile(PACKAGE_PATH) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def write_package(path: Path, files: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, contents in files.items():
            archive.writestr(name, contents)
    return path


def count(session: Session, model, *criteria) -> int:
    return int(session.scalar(select(func.count()).select_from(model).where(*criteria)) or 0)


@requires_curriculum_package
def test_actual_package_validates_all_expected_counts():
    package = validate_package(PACKAGE_PATH)
    assert package.curriculum["curriculum_version"] == "3.0.0"
    assert package.curriculum["schema_version"] == "1.0.0-draft"
    assert package.expected_counts == {
        "tracks": 5,
        "phases": 17,
        "topics": 334,
        "prerequisite_edges": 534,
        "related_topic_links": 17,
        "learning_objectives": 1002,
        "migrations": 8,
        "learner_progress_records": 89,
        "evidence_records": 9,
        "unassessed_topics": 245,
    }


@requires_curriculum_package
def test_actual_package_imports_and_matches_source(engine):
    package = validate_package(PACKAGE_PATH)
    factory = make_session_factory(engine)
    report = import_curriculum_package(PACKAGE_PATH, factory)
    assert report.actual_counts == report.expected_counts
    assert report.discrepancies == {}
    assert report.already_imported is False
    assert report.learner_state == "imported"

    with Session(engine) as session:
        release = session.get(CurriculumRelease, report.release_id)
        learner = session.scalar(select(Learner))
        assert release.curriculum_version == "3.0.0"
        assert release.schema_version == "1.0.0-draft"
        assert release.source_payload["curriculum_registry"] == package.curriculum
        assert release.source_payload["validation_report"] == package.validation_report
        assert release.source_payload["README.md"] == package.readme
        assert release.source_payload["CODEX_HANDOFF.md"] == package.handoff
        assert release.dependency_payload == package.dependencies
        assert learner.source_payload == package.learner_data

        topic = session.get(TopicVersion, (release.id, "CS-001"))
        source_topic = next(row for row in package.curriculum["topics"] if row["id"] == "CS-001")
        assert topic.source_payload == source_topic
        assert topic.source_payload["depth_frontier"] == source_topic["depth_frontier"]
        assert topic.source_payload["exercise_ids"] == []
        assert {
            row["id"]: session.get(TopicVersion, (release.id, row["id"])).source_payload
            for row in package.curriculum["topics"]
        } == {row["id"]: row for row in package.curriculum["topics"]}
        assert count(session, TrackVersion, TrackVersion.release_id == release.id) == 5
        assert count(session, PhaseVersion, PhaseVersion.release_id == release.id) == 17
        assert count(session, TopicVersion, TopicVersion.release_id == release.id) == 334
        assert count(session, TopicPhasePlacement, TopicPhasePlacement.release_id == release.id) == 334
        assert count(session, TopicTrackMembership, TopicTrackMembership.release_id == release.id) == sum(
            len(row["track_ids"]) for row in package.curriculum["topics"]
        )
        assert count(session, LearningObjective, LearningObjective.release_id == release.id) == 1002
        stored_objectives = session.scalars(
            select(LearningObjective).where(LearningObjective.release_id == release.id)
        ).all()
        assert {(row.topic_id, row.ordinal): row.source_payload for row in stored_objectives} == {
            (topic_row["id"], index): objective
            for topic_row in package.curriculum["topics"]
            for index, objective in enumerate(topic_row["objectives"])
        }
        assert count(session, PrerequisiteMember, PrerequisiteMember.release_id == release.id) == 534
        assert count(session, RelatedTopic, RelatedTopic.release_id == release.id) == 17
        assert count(session, CurriculumMigration, CurriculumMigration.release_id == release.id) == 8
        assert {
            row.retired_topic_id: row.source_payload
            for row in session.scalars(
                select(CurriculumMigration).where(CurriculumMigration.release_id == release.id)
            ).all()
        } == {row["retired_id"]: row for row in package.curriculum["migrations"]}

        related_pairs = set(
            session.execute(
                select(RelatedTopic.topic_id, RelatedTopic.related_topic_id).where(RelatedTopic.release_id == release.id)
            ).all()
        )
        expected_related = {
            (source, target)
            for source, targets in package.dependencies["related_topic_ids"].items()
            for target in targets
        }
        assert related_pairs == expected_related
        prerequisite_pairs = set(
            session.execute(
                select(PrerequisiteMember.topic_id, PrerequisiteMember.prerequisite_topic_id).where(
                    PrerequisiteMember.release_id == release.id
                )
            ).all()
        )
        assert len(prerequisite_pairs) == 534

        expected_groups = package.dependencies["prerequisite_groups"]
        multi_group_topic = next(topic_id for topic_id, groups in expected_groups.items() if len(groups) > 1)
        db_groups = session.scalars(
            select(PrerequisiteGroup)
            .where(PrerequisiteGroup.release_id == release.id, PrerequisiteGroup.topic_id == multi_group_topic)
            .order_by(PrerequisiteGroup.group_ordinal)
        ).all()
        assert len(db_groups) == len(expected_groups[multi_group_topic])
        assert [group.source_payload for group in db_groups] == expected_groups[multi_group_topic]
        and_group = next(
            (topic_id, group_index, group)
            for topic_id, groups in expected_groups.items()
            for group_index, group in enumerate(groups)
            if len(group["requires_all"]) > 1
        )
        db_members = session.scalars(
            select(PrerequisiteMember.prerequisite_topic_id).where(
                PrerequisiteMember.release_id == release.id,
                PrerequisiteMember.topic_id == and_group[0],
                PrerequisiteMember.group_ordinal == and_group[1],
            )
        ).all()
        assert set(db_members) == set(and_group[2]["requires_all"])

        progress_rows = session.scalars(
            select(LearnerProgress).where(LearnerProgress.learner_id == learner.id)
        ).all()
        assert len(progress_rows) == 89
        assert all(row.progress_status is not None and row.confidence is None for row in progress_rows)
        assert {row.topic_id: row.source_payload for row in progress_rows} == {
            row["topic_id"]: row for row in package.learner_data["records"]
        }
        progress_topic_ids = {row.topic_id for row in progress_rows}
        all_topic_ids = {row["id"] for row in package.curriculum["topics"]}
        assert len(all_topic_ids - progress_topic_ids) == 245
        assert count(session, LearnerEvidence, LearnerEvidence.learner_id == learner.id) == 9
        assert {
            row.evidence_id: row.source_payload
            for row in session.scalars(
                select(LearnerEvidence).where(LearnerEvidence.learner_id == learner.id)
            ).all()
        } == {row["id"]: row for row in package.learner_data["evidence_records"]}
        assert count(session, ProgressHistory, ProgressHistory.learner_id == learner.id) == 89
        assert count(session, TopicIdentity) == 342  # 334 active IDs plus 8 retained retired IDs.
        assert "PROB-023" not in {row.topic_id for row in session.scalars(select(TopicIdentity)).all()}


@requires_curriculum_package
def test_invalid_cross_reference_is_rejected_before_any_database_write(engine, tmp_path):
    files = package_files()
    dependency = json.loads(files["dependency_registry.json"])
    first_topic = next(iter(dependency["prerequisite_groups"]))
    dependency["prerequisite_groups"][first_topic][0]["requires_all"].append("NO-SUCH-TOPIC")
    files["dependency_registry.json"] = json.dumps(dependency).encode("utf-8")
    invalid_zip = write_package(tmp_path / "invalid.zip", files)

    factory = make_session_factory(engine)
    with pytest.raises(PackageValidationError, match="unknown Topic"):
        import_curriculum_package(invalid_zip, factory)
    with Session(engine) as session:
        assert count(session, CurriculumRelease) == 0
        assert count(session, TopicIdentity) == 0
        assert count(session, Learner) == 0


def test_cli_rejects_invalid_zip_before_database_initialization(tmp_path, monkeypatch, capsys):
    invalid_zip = tmp_path / "not-a-zip.zip"
    invalid_zip.write_bytes(b"not a zip")
    database_path = tmp_path / "must-not-be-created.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    assert main([str(invalid_zip)]) == 2
    assert not database_path.exists()
    assert "Invalid curriculum package" in capsys.readouterr().err


@requires_curriculum_package
def test_database_failure_rolls_back_entire_import(engine):
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TRIGGER fail_topic_insert BEFORE INSERT ON topic_version "
                "BEGIN SELECT RAISE(ABORT, 'forced import failure'); END"
            )
        )
    factory = make_session_factory(engine)
    with pytest.raises(IntegrityError, match="forced import failure"):
        import_curriculum_package(PACKAGE_PATH, factory)
    with Session(engine) as session:
        for model in (
            CurriculumRelease,
            TrackVersion,
            PhaseVersion,
            TopicIdentity,
            TopicVersion,
            TopicTrackMembership,
            TopicPhasePlacement,
            Learner,
            LearnerProgress,
            LearnerEvidence,
        ):
            assert count(session, model) == 0


@requires_curriculum_package
def test_duplicate_release_errors_by_default_and_skip_is_a_true_noop(engine):
    factory = make_session_factory(engine)
    first = import_curriculum_package(PACKAGE_PATH, factory)
    with Session(engine) as session:
        row = session.get(LearnerProgress, (1, "CS-001"))
        original = row.progress_status
        row.progress_status = "Revisit"
        session.commit()

    with pytest.raises(DuplicateReleaseError):
        import_curriculum_package(PACKAGE_PATH, factory)
    skipped = import_curriculum_package(PACKAGE_PATH, factory, duplicate_policy="skip")
    assert skipped.already_imported is True
    assert skipped.release_id == first.release_id
    with Session(engine) as session:
        assert count(session, CurriculumRelease) == 1
        assert session.get(LearnerProgress, (1, "CS-001")).progress_status == "Revisit"
        assert count(session, LearnerProgress, LearnerProgress.learner_id == 1) == 89
        assert original != "Revisit"


@requires_curriculum_package
def test_changed_package_cannot_overwrite_existing_learner_state(engine, tmp_path):
    factory = make_session_factory(engine)
    import_curriculum_package(PACKAGE_PATH, factory)
    with Session(engine) as session:
        row = session.get(LearnerProgress, (1, "CS-001"))
        row.progress_status = "Revisit"
        session.commit()

    files = package_files()
    files["README.md"] += b"\nAdditional static package note.\n"
    changed_zip = write_package(tmp_path / "changed-release.zip", files)
    with pytest.raises(LearnerStateConflictError):
        import_curriculum_package(changed_zip, factory)
    with Session(engine) as session:
        assert count(session, CurriculumRelease) == 1
        assert session.get(LearnerProgress, (1, "CS-001")).progress_status == "Revisit"


@requires_curriculum_package
def test_previously_retired_topic_id_cannot_be_reactivated(engine):
    with Session(engine) as session:
        old_release = CurriculumRelease(
            curriculum_version="2.0.0",
            schema_version="1.0.0-draft",
            source_digest="previous-release-digest",
            source_payload={},
            dependency_payload={},
        )
        session.add(old_release)
        session.add(TopicIdentity(topic_id="CS-001"))
        session.flush()
        session.add(
            CurriculumMigration(
                release_id=old_release.id,
                retired_topic_id="CS-001",
                disposition="merged",
                source_payload={"retired_id": "CS-001", "status": "merged"},
            )
        )
        session.commit()

    with pytest.raises(RetiredTopicIDReuseError, match="CS-001"):
        import_curriculum_package(PACKAGE_PATH, make_session_factory(engine))
    with Session(engine) as session:
        assert count(session, CurriculumRelease) == 1
