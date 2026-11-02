"""Validate and atomically import a versioned curriculum ZIP package."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import make_engine, make_session_factory
from app.db.initialize import initialize_database
from app.db.models import (
    CurriculumItem,
    CurriculumMigration,
    CurriculumMigrationDestination,
    CurriculumRelease,
    Learner,
    LearnerEvidence,
    LearnerProgress,
    LearningObjective,
    PhaseVersion,
    PrerequisiteGroup,
    PrerequisiteMember,
    ProgressHistory,
    ProgressHistoryEvidence,
    RelatedTopic,
    TopicIdentity,
    TopicPhasePlacement,
    TopicTrackMembership,
    TopicVersion,
    TrackVersion,
)
from app.schemas.curriculum import CurriculumImportInput, LearnerProgressInput


REQUIRED_FILES = {
    "curriculum_registry.json",
    "dependency_registry.json",
    "learner_progress.json",
    "validation_report.json",
    "README.md",
    "CODEX_HANDOFF.md",
}
STATIC_RELEASE_FILES = REQUIRED_FILES - {"learner_progress.json"}
MAX_PACKAGE_BYTES = 25 * 1024 * 1024


class PackageValidationError(ValueError):
    """The ZIP is malformed or its package contracts do not agree."""

    def __init__(self, issues: list[str]):
        self.issues = tuple(issues)
        super().__init__("Invalid curriculum package: " + "; ".join(issues))


class DuplicateReleaseError(RuntimeError):
    """The identical curriculum release is already present."""


class LearnerStateConflictError(RuntimeError):
    """Existing learner data differs from the package's initial snapshot."""


class AmbiguousLearnerError(RuntimeError):
    """An explicit learner ID is required when several learners exist."""


class RetiredTopicIDReuseError(RuntimeError):
    """A later release attempts to reactivate an ID already retired in history."""


@dataclass(frozen=True)
class ValidatedPackage:
    curriculum: dict[str, Any]
    dependencies: dict[str, Any]
    learner_data: dict[str, Any]
    validation_report: dict[str, Any]
    readme: str
    handoff: str
    source_digest: str
    expected_counts: dict[str, int]


@dataclass(frozen=True)
class ImportReport:
    release_id: int
    curriculum_version: str
    schema_version: str
    source_digest: str
    already_imported: bool
    learner_state: str
    expected_counts: dict[str, int]
    actual_counts: dict[str, int]
    discrepancies: dict[str, dict[str, int]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _json_object(raw: bytes, filename: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PackageValidationError([f"{filename} is not valid UTF-8 JSON: {exc}"]) from exc
    if not isinstance(value, dict):
        raise PackageValidationError([f"{filename} must contain a JSON object"])
    return value


def _check_acyclic(topic_ids: set[str], groups_by_topic: dict[str, list[dict[str, Any]]]) -> bool:
    # A prerequisite edge points from a topic to each of its required topics.
    state: dict[str, int] = {}

    def visit(topic_id: str) -> bool:
        marker = state.get(topic_id, 0)
        if marker == 1:
            return False
        if marker == 2:
            return True
        state[topic_id] = 1
        for group in groups_by_topic[topic_id]:
            for prerequisite_id in group["requires_all"]:
                if not visit(prerequisite_id):
                    return False
        state[topic_id] = 2
        return True

    return all(visit(topic_id) for topic_id in topic_ids)


def _report_counts(
    curriculum: dict[str, Any], dependencies: dict[str, Any], learner_data: dict[str, Any]
) -> dict[str, int]:
    return {
        "tracks": len(curriculum["tracks"]),
        "phases": len(curriculum["phases"]),
        "topics": len(curriculum["topics"]),
        "prerequisite_edges": sum(
            len(group["requires_all"])
            for groups in dependencies["prerequisite_groups"].values()
            for group in groups
        ),
        "related_topic_links": sum(len(items) for items in dependencies["related_topic_ids"].values()),
        "learning_objectives": sum(len(topic.get("objectives", [])) for topic in curriculum["topics"]),
        "migrations": len(curriculum["migrations"]),
        "learner_progress_records": len(learner_data["records"]),
        "evidence_records": len(learner_data["evidence_records"]),
        "unassessed_topics": learner_data["unassessed_topic_count"],
    }


def validate_package(zip_path: str | Path) -> ValidatedPackage:
    """Read and fully validate the package without opening or changing a DB."""
    path = Path(zip_path)
    issues: list[str] = []
    if not path.is_file():
        raise PackageValidationError([f"package file does not exist: {path}"])
    if path.stat().st_size > MAX_PACKAGE_BYTES:
        raise PackageValidationError([f"package exceeds {MAX_PACKAGE_BYTES} byte limit"])

    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            names = [entry.filename for entry in entries]
            if len(names) != len(set(names)):
                issues.append("ZIP contains duplicate file names")
            if set(names) != REQUIRED_FILES:
                issues.append(
                    f"ZIP file set differs from contract (missing={sorted(REQUIRED_FILES - set(names))}, "
                    f"unexpected={sorted(set(names) - REQUIRED_FILES)})"
                )
            if sum(entry.file_size for entry in entries) > MAX_PACKAGE_BYTES:
                issues.append("uncompressed package exceeds size limit")
            bad_entry = archive.testzip()
            if bad_entry:
                issues.append(f"ZIP CRC check failed for {bad_entry}")
            if issues:
                raise PackageValidationError(issues)
            raw_files = {name: archive.read(name) for name in REQUIRED_FILES}
    except (OSError, zipfile.BadZipFile, KeyError) as exc:
        raise PackageValidationError([f"cannot read ZIP: {exc}"]) from exc

    text_files: dict[str, str] = {}
    for name, raw in raw_files.items():
        try:
            text_files[name] = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            issues.append(f"{name} is not valid UTF-8: {exc}")
    if issues:
        raise PackageValidationError(issues)

    curriculum = _json_object(raw_files["curriculum_registry.json"], "curriculum_registry.json")
    dependencies = _json_object(raw_files["dependency_registry.json"], "dependency_registry.json")
    learner_data = _json_object(raw_files["learner_progress.json"], "learner_progress.json")
    report = _json_object(raw_files["validation_report.json"], "validation_report.json")

    try:
        CurriculumImportInput.model_validate(curriculum)
    except ValidationError as exc:
        issues.append(f"curriculum_registry.json schema validation failed: {exc}")
    if issues:
        raise PackageValidationError(issues[:50])

    if not isinstance(dependencies.get("prerequisite_groups"), dict) or not isinstance(dependencies.get("related_topic_ids"), dict):
        raise PackageValidationError(["dependency_registry.json must contain prerequisite_groups and related_topic_ids objects"])
    if not isinstance(learner_data.get("records"), list) or not isinstance(learner_data.get("evidence_records"), list):
        raise PackageValidationError(["learner_progress.json records and evidence_records must be arrays"])
    if not isinstance(curriculum.get("migrations"), list) or not isinstance(curriculum.get("reserved_unassigned_ids"), list):
        raise PackageValidationError(["curriculum migrations and reserved_unassigned_ids must be arrays"])

    track_ids = [row.get("id") for row in curriculum.get("tracks", [])]
    phase_ids = [row.get("id") for row in curriculum.get("phases", [])]
    topic_rows = curriculum.get("topics", [])
    topic_ids_list = [row.get("id") for row in topic_rows]
    track_ids_set, phase_ids_set, topic_ids = set(track_ids), set(phase_ids), set(topic_ids_list)
    if len(track_ids_set) != len(track_ids):
        issues.append("duplicate Track IDs")
    if len(phase_ids_set) != len(phase_ids):
        issues.append("duplicate Phase IDs")
    if len(topic_ids) != len(topic_ids_list):
        issues.append("duplicate Topic IDs")

    topic_by_id = {row["id"]: row for row in topic_rows if isinstance(row, dict) and isinstance(row.get("id"), str)}
    for topic_id, topic in topic_by_id.items():
        if topic.get("phase_id") not in phase_ids_set:
            issues.append(f"{topic_id} references unknown Phase {topic.get('phase_id')!r}")
        for track_id in topic.get("track_ids", []):
            if track_id not in track_ids_set:
                issues.append(f"{topic_id} references unknown Track {track_id!r}")
        for field in ("exercise_ids", "project_ids", "learning_resource_ids"):
            refs = topic.get(field, [])
            if not isinstance(refs, list) or len(refs) != len(set(refs)):
                issues.append(f"{topic_id}.{field} must be a duplicate-free array")
            elif refs:
                issues.append(f"{topic_id}.{field} contains links but this package has no authored item entities")

    if curriculum.get("curriculum_version") != report.get("curriculum_version"):
        issues.append("curriculum_version differs between curriculum registry and validation report")
    if dependencies.get("schema_version") != curriculum.get("schema_version"):
        issues.append("schema_version differs between curriculum and dependency registries")
    if learner_data.get("schema_version") != curriculum.get("schema_version"):
        issues.append("schema_version differs between learner and curriculum registries")

    prereq_by_topic = dependencies.get("prerequisite_groups", {})
    related_by_topic = dependencies.get("related_topic_ids", {})
    if any(not isinstance(source, str) for source in prereq_by_topic) or any(
        not isinstance(source, str) for source in related_by_topic
    ):
        raise PackageValidationError(["dependency registry Topic IDs must be strings"])
    if set(prereq_by_topic) != topic_ids:
        issues.append("dependency registry must contain an explicit prerequisite decision for every active Topic")
    if any(source not in topic_ids for source in related_by_topic):
        issues.append("related-topic registry contains an unknown source Topic")
    for source, groups in prereq_by_topic.items():
        if not isinstance(groups, list) or any(
            not isinstance(group, dict)
            or not isinstance(group.get("requires_all"), list)
            or any(not isinstance(ref, str) for ref in group.get("requires_all", []))
            for group in groups
        ):
            issues.append(f"{source} has malformed prerequisite group data")
    for source, refs in related_by_topic.items():
        if not isinstance(refs, list) or any(not isinstance(ref, str) for ref in refs):
            issues.append(f"{source} has malformed related-topic data")
    if issues:
        raise PackageValidationError(issues[:50])

    edge_count = 0
    seen_edges: set[tuple[str, str]] = set()
    for topic_id in topic_ids:
        topic = topic_by_id.get(topic_id, {})
        groups = prereq_by_topic.get(topic_id)
        if not isinstance(groups, list):
            issues.append(f"{topic_id} prerequisite decision must be an array")
            continue
        if topic.get("prerequisite_groups") != groups:
            issues.append(f"{topic_id} prerequisite groups differ between registries")
        for group_index, group in enumerate(groups):
            members = group.get("requires_all") if isinstance(group, dict) else None
            if not isinstance(members, list) or not members:
                issues.append(f"{topic_id} prerequisite group {group_index} must contain at least one requires_all member")
                continue
            if any(not isinstance(member, str) for member in members):
                issues.append(f"{topic_id} prerequisite group {group_index} members must be Topic ID strings")
                continue
            if len(members) != len(set(members)):
                issues.append(f"{topic_id} prerequisite group {group_index} has duplicate members")
            for prerequisite_id in members:
                edge_count += 1
                edge = (topic_id, prerequisite_id)
                if prerequisite_id not in topic_ids:
                    issues.append(f"{topic_id} depends on unknown Topic {prerequisite_id!r}")
                if prerequisite_id == topic_id:
                    issues.append(f"{topic_id} depends on itself")
                if edge in seen_edges:
                    issues.append(f"duplicate prerequisite edge {edge}")
                seen_edges.add(edge)
        if topic.get("dependency_review_status") != "reviewed_first_pass":
            issues.append(f"{topic_id} lacks explicit first-pass dependency review status")

    for topic_id in topic_ids:
        topic_related = topic_by_id.get(topic_id, {}).get("related_topic_ids", [])
        registry_related = related_by_topic.get(topic_id, [])
        if topic_related != registry_related:
            issues.append(f"{topic_id} related-topic links differ between registries")
        if not isinstance(registry_related, list) or any(not isinstance(ref, str) for ref in registry_related):
            issues.append(f"{topic_id} related-topic links must contain Topic ID strings")
            continue
        if len(registry_related) != len(set(registry_related)):
            issues.append(f"{topic_id} related-topic links must be duplicate-free arrays")
        for related_id in registry_related if isinstance(registry_related, list) else []:
            if related_id not in topic_ids:
                issues.append(f"{topic_id} relates to unknown Topic {related_id!r}")
            if related_id == topic_id:
                issues.append(f"{topic_id} relates to itself")

    prerequisite_refs_valid = True
    for groups in prereq_by_topic.values():
        if not isinstance(groups, list):
            prerequisite_refs_valid = False
            continue
        for group in groups:
            members = group.get("requires_all") if isinstance(group, dict) else None
            if not isinstance(members, list) or any(ref not in topic_ids for ref in members):
                prerequisite_refs_valid = False
    if set(prereq_by_topic) == topic_ids and prerequisite_refs_valid and not _check_acyclic(topic_ids, prereq_by_topic):
        issues.append("union of prerequisite edges contains a cycle")

    migrations = curriculum.get("migrations", [])
    retired_ids: list[str] = []
    for migration in migrations:
        if not isinstance(migration, dict):
            issues.append("migration entries must be objects")
            continue
        retired_id = migration.get("retired_id")
        retired_ids.append(retired_id)
        if not isinstance(retired_id, str) or retired_id in topic_ids:
            issues.append(f"invalid or active retired Topic ID {retired_id!r}")
        if not isinstance(migration.get("status"), str):
            issues.append(f"migration {retired_id!r} must have a string status")
        if migration.get("reason") is not None and not isinstance(migration.get("reason"), str):
            issues.append(f"migration {retired_id!r} reason must be a string or null")
        destinations = migration.get("destination_ids")
        if destinations is None:
            destination = migration.get("destination_id")
            destinations = [destination] if destination is not None else []
        if not isinstance(destinations, list):
            issues.append(f"migration {retired_id!r} destinations must be an array or destination_id")
            continue
        for destination_id in destinations:
            if not isinstance(destination_id, str):
                issues.append(f"migration {retired_id!r} destination IDs must be strings")
                continue
            if destination_id not in topic_ids:
                issues.append(f"migration {retired_id!r} points to unknown destination {destination_id!r}")
        if all(isinstance(destination_id, str) for destination_id in destinations) and len(destinations) != len(set(destinations)):
            issues.append(f"migration {retired_id!r} has duplicate destinations")
    if all(isinstance(retired_id, str) for retired_id in retired_ids) and len(retired_ids) != len(set(retired_ids)):
        issues.append("migration ledger contains duplicate retired IDs")
    reserved_ids = curriculum.get("reserved_unassigned_ids", [])
    if any(not isinstance(reserved_id, str) for reserved_id in reserved_ids):
        issues.append("reserved Topic IDs must be strings")
    elif len(reserved_ids) != len(set(reserved_ids)):
        issues.append("reserved Topic IDs contain duplicates")
    if all(isinstance(retired_id, str) for retired_id in retired_ids) and all(isinstance(x, str) for x in reserved_ids) and set(reserved_ids) & (topic_ids | set(retired_ids)):
        issues.append("reserved Topic IDs overlap active or retired Topic IDs")

    try:
        record_models = [LearnerProgressInput.model_validate(record) for record in learner_data["records"]]
    except (ValidationError, KeyError, TypeError) as exc:
        raise PackageValidationError([f"learner progress schema validation failed: {exc}"]) from exc
    progress_ids = [record.topic_id for record in record_models]
    expected_statuses = ["Not started", "Learning", "Practicing", "Solid", "Revisit"]
    if learner_data.get("canonical_statuses") != expected_statuses:
        issues.append("learner progress canonical_statuses differ from the accepted contract")
    confidence_scale = learner_data.get("confidence_scale", {})
    if not isinstance(confidence_scale, dict) or confidence_scale.get("min") != 1 or confidence_scale.get("max") != 5:
        issues.append("learner confidence scale must be 1 through 5")
    if not isinstance(confidence_scale, dict) or confidence_scale.get("independent_of_progress") is not True:
        issues.append("learner confidence must be declared independent of progress")
    if len(progress_ids) != len(set(progress_ids)):
        issues.append("learner progress contains duplicate Topic records")
    if any(topic_id not in topic_ids for topic_id in progress_ids):
        issues.append("learner progress references an unknown or retired Topic ID")
    for record in learner_data.get("records", []):
        reviewed = record.get("last_reviewed")
        if reviewed is not None:
            try:
                datetime.fromisoformat(reviewed.replace("Z", "+00:00"))
            except (AttributeError, ValueError):
                issues.append(f"{record.get('topic_id')} has invalid last_reviewed value {reviewed!r}")

    evidence_records = learner_data["evidence_records"]
    if any(
        not isinstance(record, dict)
        or not isinstance(record.get("id"), str)
        or not isinstance(record.get("type"), str)
        or not isinstance(record.get("description"), str)
        for record in evidence_records
    ):
        raise PackageValidationError(["evidence records require string id, type, and description fields"])
    evidence_ids = [record.get("id") for record in evidence_records]
    if len(evidence_ids) != len(set(evidence_ids)):
        issues.append("evidence IDs are not unique")
    evidence_id_set = set(evidence_ids)
    for row in learner_data["records"]:
        refs = row.get("evidence_ids", [])
        if not isinstance(refs, list) or any(not isinstance(ref, str) for ref in refs):
            issues.append(f"{row.get('topic_id')} evidence_ids must be an array")
        elif len(refs) != len(set(refs)):
            issues.append(f"{row.get('topic_id')} evidence_ids contain duplicates")
        elif any(evidence_id not in evidence_id_set for evidence_id in refs):
            issues.append(f"{row.get('topic_id')} references an undefined evidence ID")

    expected = _report_counts(curriculum, dependencies, learner_data)
    expected_from_release_report = {
        "tracks": report.get("track_count"),
        "phases": report.get("phase_count"),
        "topics": report.get("active_topic_count"),
        "prerequisite_edges": report.get("prerequisite_edge_count"),
        "related_topic_links": sum(len(values) for values in related_by_topic.values()),
        "learning_objectives": report.get("topic_specific_objective_count"),
        "migrations": report.get("migration_count"),
        "learner_progress_records": report.get("learner_progress_records"),
        "evidence_records": len(evidence_records),
        "unassessed_topics": report.get("learner_unassessed_topics"),
    }
    for key, actual in expected.items():
        if expected_from_release_report.get(key) != actual:
            issues.append(
                f"validation report {key}={expected_from_release_report.get(key)!r}, actual package value={actual}"
            )
    if report.get("unique_topic_ids") != len(topic_ids) or report.get("duplicate_topic_ids") != 0:
        issues.append("validation report Topic ID uniqueness figures do not match package")
    if dependencies.get("reviewed_topic_count") != len(topic_ids) or dependencies.get("active_topic_count") != len(topic_ids):
        issues.append("dependency registry review coverage counts do not match active Topics")
    if dependencies.get("edge_count") != edge_count:
        issues.append("dependency registry edge_count does not match prerequisite members")
    if dependencies.get("pending_topic_ids") != []:
        issues.append("dependency registry has pending Topic decisions")
    validation = dependencies.get("validation", {})
    if not isinstance(validation, dict):
        raise PackageValidationError(["dependency_registry.json validation field must be an object"])
    if validation.get("unresolved_references") != []:
        issues.append("dependency registry validation reports unresolved references")
    cycle_check = validation.get("cycle_check_union_of_alternative_edges", {})
    if cycle_check.get("performed") is not True or cycle_check.get("acyclic") is not True:
        issues.append("dependency registry validation does not report an acyclic union graph")
    coverage = validation.get("coverage_check", {})
    if coverage.get("active_topics") != len(topic_ids) or coverage.get("reviewed_topics") != len(topic_ids) or coverage.get("pending_topics") != 0:
        issues.append("dependency registry validation coverage counts do not match the package")
    if report.get("validation_status") != "release_candidate":
        issues.append("validation report is not marked release_candidate")
    if report.get("dependency_reviewed_topics") != len(topic_ids) or report.get("dependency_pending_topics") != 0:
        issues.append("validation report dependency review counts do not match the package")
    if report.get("unresolved_dependency_references") != 0 or report.get("duplicate_dependency_edges") != 0:
        issues.append("validation report indicates unresolved or duplicate prerequisite edges")
    if report.get("dependency_union_graph_acyclic") is not True:
        issues.append("validation report does not mark the prerequisite union graph acyclic")
    if report.get("related_topic_sources") != len(related_by_topic):
        issues.append("validation report related-topic source count does not match the package")
    if learner_data.get("unassessed_topic_count") != len(topic_ids) - len(progress_ids):
        issues.append("learner unassessed count does not match missing progress records")

    if issues:
        # Avoid an unbounded exception for hostile input with thousands of bad rows.
        raise PackageValidationError(issues[:50])

    digest = hashlib.sha256()
    for name in sorted(STATIC_RELEASE_FILES):
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(raw_files[name])
        digest.update(b"\0")

    return ValidatedPackage(
        curriculum=curriculum,
        dependencies=dependencies,
        learner_data=learner_data,
        validation_report=report,
        readme=text_files["README.md"],
        handoff=text_files["CODEX_HANDOFF.md"],
        source_digest=digest.hexdigest(),
        expected_counts=expected,
    )


def _get_duplicate_release(session: Session, package: ValidatedPackage) -> CurriculumRelease | None:
    return session.scalar(
        select(CurriculumRelease).where(
            CurriculumRelease.curriculum_version == package.curriculum["curriculum_version"],
            CurriculumRelease.schema_version == package.curriculum["schema_version"],
            CurriculumRelease.source_digest == package.source_digest,
        )
    )


def _resolve_learner(session: Session, learner_id: int | None) -> tuple[Learner, bool]:
    if learner_id is not None:
        learner = session.get(Learner, learner_id)
        if learner is None:
            raise ValueError(f"learner_id {learner_id} does not exist")
        return learner, False
    learners = session.scalars(select(Learner).order_by(Learner.id)).all()
    if len(learners) > 1:
        raise AmbiguousLearnerError("Pass learner_id when the database contains multiple learners")
    if learners:
        return learners[0], False
    learner = Learner(display_name=None, source_payload={})
    session.add(learner)
    session.flush()
    return learner, True


def _find_learner_without_creating(session: Session, learner_id: int | None) -> Learner | None:
    if learner_id is not None:
        learner = session.get(Learner, learner_id)
        if learner is None:
            raise ValueError(f"learner_id {learner_id} does not exist")
        return learner
    learners = session.scalars(select(Learner).order_by(Learner.id)).all()
    if len(learners) > 1:
        raise AmbiguousLearnerError("Pass learner_id when the database contains multiple learners")
    return learners[0] if learners else None


def _existing_learner_data_matches(session: Session, learner: Learner, package: ValidatedPackage) -> bool:
    expected_records = {row["topic_id"]: row for row in package.learner_data["records"]}
    current_records = session.scalars(
        select(LearnerProgress).where(LearnerProgress.learner_id == learner.id)
    ).all()
    current_by_topic = {row.topic_id: row for row in current_records}
    if set(current_by_topic) != set(expected_records):
        return False
    for topic_id, raw in expected_records.items():
        row = current_by_topic[topic_id]
        model = LearnerProgressInput.model_validate(raw)
        if (
            row.progress_status != model.progress_status
            or row.confidence != model.confidence
            or row.progress_scope != model.progress_scope
            or row.notes != model.notes
            or row.source_payload != raw
        ):
            return False
    expected_evidence = {row["id"]: row for row in package.learner_data["evidence_records"]}
    current_evidence = session.scalars(
        select(LearnerEvidence).where(LearnerEvidence.learner_id == learner.id)
    ).all()
    current_evidence_by_id = {row.evidence_id: row for row in current_evidence}
    if set(current_evidence_by_id) != set(expected_evidence):
        return False
    return all(
        current_evidence_by_id[evidence_id].evidence_type == raw["type"]
        and current_evidence_by_id[evidence_id].description == raw["description"]
        and current_evidence_by_id[evidence_id].source_payload == raw
        for evidence_id, raw in expected_evidence.items()
    ) and learner.source_payload == package.learner_data


def _actual_counts(session: Session, release: CurriculumRelease, learner: Learner | None) -> dict[str, int]:
    rid = release.id
    scalar_count = lambda model, *criteria: int(session.scalar(select(func.count()).select_from(model).where(*criteria)) or 0)
    topic_ids = select(TopicVersion.topic_id).where(TopicVersion.release_id == rid)
    package_progress_ids = {row["topic_id"] for row in session.info.get("expected_progress_rows", [])}
    if learner is None:
        progress_count = 0
    elif package_progress_ids:
        progress_count = scalar_count(
            LearnerProgress,
            LearnerProgress.learner_id == learner.id,
            LearnerProgress.topic_id.in_(package_progress_ids),
        )
    else:
        progress_count = scalar_count(LearnerProgress, LearnerProgress.learner_id == learner.id)
    expected_evidence_ids = session.info.get("expected_evidence_ids", set())
    evidence_count = 0 if learner is None else (
        scalar_count(
            LearnerEvidence,
            LearnerEvidence.learner_id == learner.id,
            LearnerEvidence.evidence_id.in_(expected_evidence_ids),
        )
        if expected_evidence_ids
        else scalar_count(LearnerEvidence, LearnerEvidence.learner_id == learner.id)
    )
    unassessed_count = (
        scalar_count(TopicVersion, TopicVersion.release_id == rid)
        if learner is None
        else scalar_count(
            TopicVersion,
            TopicVersion.release_id == rid,
            ~TopicVersion.topic_id.in_(
                select(LearnerProgress.topic_id).where(
                    LearnerProgress.learner_id == learner.id,
                    LearnerProgress.topic_id.in_(topic_ids),
                )
            ),
        )
    )
    return {
        "tracks": scalar_count(TrackVersion, TrackVersion.release_id == rid),
        "phases": scalar_count(PhaseVersion, PhaseVersion.release_id == rid),
        "topics": scalar_count(TopicVersion, TopicVersion.release_id == rid),
        "prerequisite_edges": scalar_count(PrerequisiteMember, PrerequisiteMember.release_id == rid),
        "related_topic_links": scalar_count(RelatedTopic, RelatedTopic.release_id == rid),
        "learning_objectives": scalar_count(LearningObjective, LearningObjective.release_id == rid),
        "migrations": scalar_count(CurriculumMigration, CurriculumMigration.release_id == rid),
        "learner_progress_records": progress_count,
        "evidence_records": evidence_count,
        "unassessed_topics": unassessed_count,
    }


def _make_report(
    session: Session,
    release: CurriculumRelease,
    learner: Learner | None,
    package: ValidatedPackage,
    *,
    already_imported: bool,
    learner_state: str,
) -> ImportReport:
    session.info["expected_progress_rows"] = package.learner_data["records"]
    session.info["expected_evidence_ids"] = {row["id"] for row in package.learner_data["evidence_records"]}
    actual = _actual_counts(session, release, learner)
    expected = package.expected_counts
    discrepancies = {
        key: {"expected": expected[key], "actual": actual[key]}
        for key in expected
        if expected[key] != actual[key]
    }
    return ImportReport(
        release_id=release.id,
        curriculum_version=release.curriculum_version,
        schema_version=release.schema_version,
        source_digest=release.source_digest or "",
        already_imported=already_imported,
        learner_state=learner_state,
        expected_counts=expected,
        actual_counts=actual,
        discrepancies=discrepancies,
    )


def _populate_learner(session: Session, learner: Learner, data: dict[str, Any], release_id: int) -> None:
    learner.source_payload = data
    evidence_by_id: dict[str, LearnerEvidence] = {}
    for raw in data["evidence_records"]:
        evidence = LearnerEvidence(
            learner_id=learner.id,
            evidence_id=raw["id"],
            evidence_type=raw["type"],
            description=raw["description"],
            source_payload=raw,
        )
        session.add(evidence)
        evidence_by_id[raw["id"]] = evidence
    for raw in data["records"]:
        record = LearnerProgressInput.model_validate(raw)
        current = LearnerProgress(
            learner_id=learner.id,
            topic_id=record.topic_id,
            progress_status=record.progress_status,
            confidence=record.confidence,
            progress_scope=record.progress_scope,
            notes=record.notes,
            source_payload=raw,
        )
        session.add(current)
        occurred_at = raw.get("last_reviewed")
        history = ProgressHistory(
            learner_id=learner.id,
            topic_id=record.topic_id,
            event_type="package_import_snapshot",
            progress_status=record.progress_status,
            confidence=record.confidence,
            progress_scope=record.progress_scope,
            notes=record.notes,
            source_release_id=release_id,
            source_payload=raw,
            occurred_at=datetime.fromisoformat(occurred_at.replace("Z", "+00:00")) if occurred_at else None,
        )
        session.add(history)
        for evidence_id in raw["evidence_ids"]:
            session.flush()
            session.add(
                ProgressHistoryEvidence(
                    history_id=history.id,
                    learner_id=learner.id,
                    topic_id=record.topic_id,
                    evidence_id=evidence_id,
                )
            )


def _write_curriculum(session: Session, package: ValidatedPackage, learner_id: int) -> CurriculumRelease:
    curriculum = package.curriculum
    release = CurriculumRelease(
        curriculum_version=curriculum["curriculum_version"],
        schema_version=curriculum["schema_version"],
        release_status=curriculum.get("status"),
        source_digest=package.source_digest,
        source_payload={
            "curriculum_registry": curriculum,
            "validation_report": package.validation_report,
            "README.md": package.readme,
            "CODEX_HANDOFF.md": package.handoff,
        },
        dependency_payload=package.dependencies,
    )
    session.add(release)
    session.flush()
    release_id = release.id

    session.add_all(
        TrackVersion(release_id=release_id, track_id=row["id"], title=row["title"], source_payload=row)
        for row in curriculum["tracks"]
    )
    session.add_all(
        PhaseVersion(release_id=release_id, phase_id=row["id"], title=row["title"], source_payload=row)
        for row in curriculum["phases"]
    )
    session.flush()

    active_ids = {row["id"] for row in curriculum["topics"]}
    retired_ids = {row["retired_id"] for row in curriculum["migrations"]}
    identities = set(session.scalars(select(TopicIdentity.topic_id).where(TopicIdentity.topic_id.in_(active_ids | retired_ids))))
    session.add_all(TopicIdentity(topic_id=topic_id) for topic_id in (active_ids | retired_ids) - identities)
    session.flush()

    for topic in curriculum["topics"]:
        topic_id = topic["id"]
        session.add(
            TopicVersion(
                release_id=release_id,
                topic_id=topic_id,
                title=topic["title"],
                description=topic.get("description"),
                pathway=topic.get("pathway"),
                current_priority=topic.get("current_priority"),
                registry_status=topic.get("registry_status"),
                dependency_review_status=topic.get("dependency_review_status"),
                source_payload=topic,
            )
        )
    session.flush()

    prerequisite_groups: list[PrerequisiteGroup] = []
    prerequisite_members: list[PrerequisiteMember] = []
    for topic in curriculum["topics"]:
        topic_id = topic["id"]
        session.add(TopicPhasePlacement(release_id=release_id, topic_id=topic_id, phase_id=topic["phase_id"]))
        session.add_all(
            TopicTrackMembership(release_id=release_id, topic_id=topic_id, track_id=track_id)
            for track_id in topic["track_ids"]
        )
        session.add_all(
            LearningObjective(
                release_id=release_id,
                topic_id=topic_id,
                ordinal=index,
                objective_type=objective.get("type"),
                text=objective["text"],
                source_payload=objective,
            )
            for index, objective in enumerate(topic.get("objectives", []))
        )
        for group_index, group in enumerate(package.dependencies["prerequisite_groups"][topic_id]):
            prerequisite_groups.append(
                PrerequisiteGroup(
                    release_id=release_id,
                    topic_id=topic_id,
                    group_ordinal=group_index,
                    source_payload=group,
                )
            )
            prerequisite_members.extend(
                PrerequisiteMember(
                    release_id=release_id,
                    topic_id=topic_id,
                    group_ordinal=group_index,
                    prerequisite_topic_id=prerequisite_id,
                )
                for prerequisite_id in group["requires_all"]
            )
        session.add_all(
            RelatedTopic(release_id=release_id, topic_id=topic_id, related_topic_id=related_id)
            for related_id in package.dependencies["related_topic_ids"].get(topic_id, [])
        )

    session.add_all(prerequisite_groups)
    session.flush()
    session.add_all(prerequisite_members)
    session.flush()

    migration_destinations: list[CurriculumMigrationDestination] = []
    for migration in curriculum["migrations"]:
        retired_id = migration["retired_id"]
        session.add(
            CurriculumMigration(
                release_id=release_id,
                retired_topic_id=retired_id,
                disposition=migration["status"],
                reason=migration.get("reason"),
                source_payload=migration,
            )
        )
        destinations = migration.get("destination_ids")
        if destinations is None:
            destination = migration.get("destination_id")
            destinations = [destination] if destination is not None else []
        migration_destinations.extend(
            CurriculumMigrationDestination(
                release_id=release_id,
                retired_topic_id=retired_id,
                destination_topic_id=destination_id,
            )
            for destination_id in destinations
        )
    session.flush()
    session.add_all(migration_destinations)

    # Current package link arrays are empty. A future package must add item entities
    # before non-empty references can be represented by the typed FK table.
    for item_kind, field in (
        ("exercise", "exercise_ids"),
        ("project", "project_ids"),
        ("learning_resource", "learning_resource_ids"),
    ):
        for topic in curriculum["topics"]:
            for item_id in topic.get(field, []):
                session.add(CurriculumItem(release_id=release_id, item_kind=item_kind, item_id=item_id, source_payload={}))
                session.add(TopicCurriculumItem(release_id=release_id, topic_id=topic["id"], item_kind=item_kind, item_id=item_id))

    return release


def import_curriculum_package(
    zip_path: str | Path,
    session_factory: sessionmaker[Session],
    *,
    learner_id: int | None = None,
    duplicate_policy: Literal["error", "skip"] = "error",
) -> ImportReport:
    """Validate first, then import the full release and initial learner snapshot atomically.

    Duplicate behavior is explicit: the default raises without writes; ``skip`` is
    a no-op only for an identical curriculum payload digest. Existing learner state
    is never updated. If it differs from a changed package snapshot, the whole
    import aborts rather than overwriting or dropping either version.
    """
    package = validate_package(zip_path)
    with session_factory() as session:
        if duplicate_policy not in ("error", "skip"):
            raise ValueError(f"unsupported duplicate_policy: {duplicate_policy}")
        with session.begin():
            duplicate = _get_duplicate_release(session, package)
            if duplicate is not None:
                if duplicate_policy == "error":
                    raise DuplicateReleaseError(
                        f"curriculum {duplicate.curriculum_version} / schema {duplicate.schema_version} "
                        f"with digest {duplicate.source_digest} is already imported"
                    )
                learner = _find_learner_without_creating(session, learner_id)
                return _make_report(
                    session,
                    duplicate,
                    learner,
                    package,
                    already_imported=True,
                    learner_state="unchanged_duplicate_skip",
                )
            active_topic_ids = {topic["id"] for topic in package.curriculum["topics"]}
            historically_retired_ids = set(session.scalars(select(CurriculumMigration.retired_topic_id)))
            reused_ids = sorted(active_topic_ids & historically_retired_ids)
            if reused_ids:
                raise RetiredTopicIDReuseError(
                    "release attempts to reactivate retired Topic IDs: " + ", ".join(reused_ids)
                )
            learner, learner_created = _resolve_learner(session, learner_id)
            learner_has_data = (
                session.scalar(select(func.count()).select_from(LearnerProgress).where(LearnerProgress.learner_id == learner.id))
                or session.scalar(select(func.count()).select_from(LearnerEvidence).where(LearnerEvidence.learner_id == learner.id))
                or session.scalar(select(func.count()).select_from(ProgressHistory).where(ProgressHistory.learner_id == learner.id))
            )
            learner_matches = not learner_has_data or _existing_learner_data_matches(session, learner, package)
            if not learner_matches:
                raise LearnerStateConflictError(
                    "existing learner progress/evidence differs from the package snapshot; no data was changed. "
                    "Reconcile the learner snapshot explicitly before importing this changed package."
                )

            release = _write_curriculum(session, package, learner.id)
            if not learner_has_data and not learner_created and learner.source_payload not in ({}, package.learner_data):
                raise LearnerStateConflictError("existing learner metadata differs from the package snapshot")
            learner_state = "imported"
            if learner_matches:
                if learner_has_data:
                    # Identical pre-existing data is left untouched; no duplicate history rows are added.
                    learner_state = "already_identical"
                else:
                    _populate_learner(session, learner, package.learner_data, release.id)
                    learner_state = "imported"
            session.flush()
            report = _make_report(
                session,
                release,
                learner,
                package,
                already_imported=False,
                learner_state=learner_state,
            )
        return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import the First-Principles curriculum package into local SQLite")
    parser.add_argument("package", help="path to a local curriculum ZIP")
    parser.add_argument("--duplicate-policy", choices=("error", "skip"), default="error")
    parser.add_argument("--learner-id", type=int)
    parser.add_argument("--report-out", type=Path, help="also write the expected/actual count report to this JSON path")
    args = parser.parse_args(argv)
    engine = None
    try:
        # Reject a malformed package before even creating/upgrading the local DB.
        validate_package(args.package)
        initialize_database()
        engine = make_engine()
        factory = make_session_factory(engine)
        report = import_curriculum_package(
            args.package,
            factory,
            learner_id=args.learner_id,
            duplicate_policy=args.duplicate_policy,
        )
        output = json.dumps(report.to_dict(), indent=2, ensure_ascii=False)
        if args.report_out:
            args.report_out.parent.mkdir(parents=True, exist_ok=True)
            args.report_out.write_text(output + "\n", encoding="utf-8")
        print(output)
        return 0
    except (
        PackageValidationError,
        DuplicateReleaseError,
        LearnerStateConflictError,
        AmbiguousLearnerError,
        RetiredTopicIDReuseError,
        ValueError,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
