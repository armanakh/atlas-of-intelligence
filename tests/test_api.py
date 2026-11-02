import os
import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import (
    ActiveCurriculumRelease,
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
from app.db.database import make_session_factory
from app.importer import import_curriculum_package
from app.main import create_app


PACKAGE_PATH = Path(os.environ.get(
    "ATLAS_TEST_CURRICULUM_PACKAGE",
    str(Path(__file__).resolve().parents[1] / "first_principles_ai_curriculum_v3_0_codex_clarified_package.zip"),
))
requires_curriculum_package = pytest.mark.skipif(
    not PACKAGE_PATH.is_file(),
    reason="Actual curriculum integration data is not bundled; set ATLAS_TEST_CURRICULUM_PACKAGE to a local package path.",
)


@dataclass
class LocalResponse:
    status_code: int
    body: bytes

    def json(self):
        return json.loads(self.body or b"null")


class LocalASGIClient:
    """Tiny in-process ASGI harness; avoids an optional HTTP client dependency."""

    def __init__(self, app):
        self.app = app

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def get(self, path):
        return self._request("GET", path)

    def put(self, path, json=None):
        return self._request("PUT", path, json)

    def patch(self, path, json=None):
        return self._request("PATCH", path, json)

    def delete(self, path):
        return self._request("DELETE", path)

    def _request(self, method, path, payload=None):
        parsed = urlsplit(path)
        body = json.dumps(payload).encode("utf-8") if payload is not None else b""
        messages = []
        body_sent = False

        async def receive():
            nonlocal body_sent
            if not body_sent:
                body_sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            return {"type": "http.disconnect"}

        async def send(message):
            messages.append(message)

        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": parsed.path,
            "raw_path": parsed.path.encode("ascii"),
            "query_string": parsed.query.encode("ascii"),
            "root_path": "",
            "headers": [(b"host", b"testserver"), (b"content-type", b"application/json")],
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
        }
        try:
            asyncio.run(self.app(scope, receive, send))
        except Exception:
            # Starlette's ServerErrorMiddleware re-raises after the installed
            # exception handler has emitted its sanitized 500 response.
            if not any(message["type"] == "http.response.start" for message in messages):
                raise
        status_code = next(message["status"] for message in messages if message["type"] == "http.response.start")
        response_body = b"".join(
            message.get("body", b"") for message in messages if message["type"] == "http.response.body"
        )
        return LocalResponse(status_code, response_body)


def seed_release(session, version, topic_ids, *, structurally_validated=True):
    payload = {}
    if structurally_validated:
        payload = {"validation_report": {"content_maturity": {"structural_validation": "passed"}}}
    release = CurriculumRelease(
        curriculum_version=version,
        schema_version="1.0.0-draft",
        release_status="curriculum_release_candidate",
        source_digest=f"digest-{version}",
        source_payload=payload,
        dependency_payload={},
    )
    session.add(release)
    session.flush()
    for topic_id in topic_ids:
        if session.get(TopicIdentity, topic_id) is None:
            session.add(TopicIdentity(topic_id=topic_id))
            session.flush()
        session.add(
            TopicVersion(
                release_id=release.id,
                topic_id=topic_id,
                title=f"{version} {topic_id}",
                description=f"Description {topic_id}",
                pathway="core",
                source_payload={"id": topic_id, "title": f"{version} {topic_id}", "future_field": {"kept": True}},
            )
        )
    session.flush()
    return release


@pytest.fixture
def api_context(engine):
    with Session(engine) as session:
        first = seed_release(session, "3.0.0", ("T", "A", "R", "ALT", "D", "UNASSESSED"))
        second = seed_release(session, "3.1.0", ("T", "A"))
        session.add_all(
            [
                TrackVersion(release_id=first.id, track_id="TR-A", title="Track A", source_payload={"id": "TR-A", "title": "Track A", "optional": 7}),
                PhaseVersion(release_id=first.id, phase_id="PH01", title="Phase 1", source_payload={"id": "PH01", "title": "Phase 1"}),
            ]
        )
        session.flush()
        session.add_all(
            [
                TopicTrackMembership(release_id=first.id, topic_id="T", track_id="TR-A"),
                TopicTrackMembership(release_id=first.id, topic_id="A", track_id="TR-A"),
                TopicPhasePlacement(release_id=first.id, topic_id="T", phase_id="PH01"),
                LearningObjective(release_id=first.id, topic_id="T", ordinal=0, objective_type="know", text="Explain it", source_payload={"type": "know", "text": "Explain it", "extension": [1]}),
                PrerequisiteGroup(release_id=first.id, topic_id="T", group_ordinal=0, source_payload={"requires_all": ["A"]}),
                PrerequisiteGroup(release_id=first.id, topic_id="T", group_ordinal=1, source_payload={"requires_all": ["ALT"]}),
                PrerequisiteMember(release_id=first.id, topic_id="T", group_ordinal=0, prerequisite_topic_id="A"),
                PrerequisiteMember(release_id=first.id, topic_id="T", group_ordinal=1, prerequisite_topic_id="ALT"),
                PrerequisiteGroup(release_id=first.id, topic_id="D", group_ordinal=0, source_payload={"requires_all": ["T"]}),
                PrerequisiteMember(release_id=first.id, topic_id="D", group_ordinal=0, prerequisite_topic_id="T"),
                RelatedTopic(release_id=first.id, topic_id="T", related_topic_id="R"),
            ]
        )
        learner = Learner(display_name=None, source_payload={})
        second_learner = Learner(display_name="Second", source_payload={})
        session.add_all([learner, second_learner])
        session.commit()
        ctx = {
            "release_id": first.public_id,
            "second_release_id": second.public_id,
            "learner_id": learner.id,
            "second_learner_id": second_learner.id,
        }
    return create_app(engine=engine), ctx


def test_release_ids_active_selection_and_no_internal_release_id(api_context):
    app, ctx = api_context
    with LocalASGIClient(app) as client:
        releases = client.get("/api/v1/curriculum/releases")
        assert releases.status_code == 200
        data = releases.json()["items"]
        assert {row["release_id"] for row in data} == {ctx["release_id"], ctx["second_release_id"]}
        assert all("id" not in row for row in data)
        assert UUID(ctx["release_id"])

        no_active = client.get("/api/v1/curriculum/active-release")
        assert no_active.status_code == 409
        assert no_active.json()["error"]["code"] == "active_release_not_selected"

        selected = client.put("/api/v1/curriculum/active-release", json={"release_id": ctx["release_id"]})
        assert selected.status_code == 200
        assert selected.json()["release_id"] == ctx["release_id"]
        assert "id" not in selected.json()
        assert client.get("/api/v1/curriculum/active-release").json()["release_id"] == ctx["release_id"]

        replaced = client.put("/api/v1/curriculum/active-release", json={"release_id": ctx["second_release_id"]})
        assert replaced.status_code == 200
        with Session(app.state.session_factory.kw["bind"]) as session:
            assert session.scalar(select(func.count()).select_from(ActiveCurriculumRelease)) == 1
            pointer = session.get(ActiveCurriculumRelease, 1)
            assert session.get(CurriculumRelease, pointer.release_id).public_id == ctx["second_release_id"]


def test_active_release_selection_rejects_unvalidated_and_unknown_release(api_context, engine):
    app, ctx = api_context
    with Session(engine) as session:
        invalid = seed_release(session, "3.2.0", ("INVALID",), structurally_validated=False)
        invalid_public_id = invalid.public_id
        session.commit()
    with LocalASGIClient(app) as client:
        response = client.put("/api/v1/curriculum/active-release", json={"release_id": invalid_public_id})
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "release_not_validated"
        missing = client.put("/api/v1/curriculum/active-release", json={"release_id": str(uuid4())})
        assert missing.status_code == 404
        assert missing.json()["error"]["code"] == "release_not_found"


def test_current_learner_returns_not_found_without_creating_a_learner(engine):
    app = create_app(engine=engine)
    with LocalASGIClient(app) as client:
        response = client.get("/api/v1/learners/current")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "current_learner_not_found",
            "message": "No local learner exists",
            "details": {"learner_count": 0},
        }
    }
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Learner)) == 0


def test_current_learner_returns_minimal_public_representation(engine):
    with Session(engine) as session:
        learner = Learner(display_name="Arman", source_payload={"private_import_data": "not public"})
        session.add(learner)
        session.commit()
        learner_id = learner.id

    app = create_app(engine=engine)
    with LocalASGIClient(app) as client:
        response = client.get("/api/v1/learners/current")

    assert response.status_code == 200
    assert response.json() == {"learner_id": learner_id, "display_name": "Arman"}
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Learner)) == 1


def test_current_learner_returns_ambiguity_for_multiple_learners(engine):
    with Session(engine) as session:
        session.add_all(
            [
                Learner(display_name=None, source_payload={}),
                Learner(display_name="Second", source_payload={}),
                Learner(display_name="Third", source_payload={}),
            ]
        )
        session.commit()

    app = create_app(engine=engine)
    with LocalASGIClient(app) as client:
        response = client.get("/api/v1/learners/current")

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "current_learner_ambiguous",
            "message": "A current learner cannot be resolved because multiple local learners exist",
            "details": {"learner_count": 3},
        }
    }


def test_active_release_and_public_id_database_constraints(engine):
    with Session(engine) as session:
        first = seed_release(session, "3.0.0", ("A",))
        second = seed_release(session, "3.1.0", ("A",))
        first_id, second_id = first.id, second.id
        session.add(ActiveCurriculumRelease(singleton_id=1, release_id=first.id))
        session.commit()
        session.add(ActiveCurriculumRelease(singleton_id=2, release_id=second.id))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        session.add(ActiveCurriculumRelease(singleton_id=1, release_id=second_id))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        assert first_id != second_id

        session.add(
            CurriculumRelease(
                curriculum_version="duplicate-public-id",
                schema_version="x",
                public_id=first.public_id,
                source_payload={},
                dependency_payload={},
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_curriculum_read_contract_metadata_hierarchy_and_release_scoping(api_context):
    app, ctx = api_context
    with LocalASGIClient(app) as client:
        root = f"/api/v1/curriculum/releases/{ctx['release_id']}"
        detail = client.get(f"{root}/topics/T")
        assert detail.status_code == 200
        topic = detail.json()
        assert topic["track_ids"] == ["TR-A"]
        assert topic["phase_id"] == "PH01"
        assert topic["metadata"]["future_field"] == {"kept": True}
        assert topic["objectives"][0]["metadata"]["extension"] == [1]
        assert topic["prerequisite_groups"] == [
            {"group_ordinal": 0, "logic_within_group": "AND", "requires_all": ["A"]},
            {"group_ordinal": 1, "logic_within_group": "AND", "requires_all": ["ALT"]},
        ]
        assert topic["related_topic_ids"] == ["R"]

        deps = client.get(f"{root}/topics/T/dependencies").json()
        assert deps["related_topic_ids"] == ["R"]
        assert "R" not in [item for group in deps["prerequisite_groups"] for item in group["requires_all"]]
        assert deps["direct_dependent_ids"] == ["D"]

        tree = client.get(f"{root}/hierarchy").json()
        assert tree["tracks"][0]["topic_ids"] == ["A", "T"]
        assert tree["phases"][0]["topic_ids"] == ["T"]
        track_filter = client.get(f"{root}/topics?track_id=TR-A&limit=1")
        assert track_filter.status_code == 200
        assert len(track_filter.json()["items"]) == 1
        assert track_filter.json()["next_cursor"]

        absent_release_topic = client.get(
            f"/api/v1/curriculum/releases/{ctx['second_release_id']}/topics/UNASSESSED"
        )
        assert absent_release_topic.status_code == 404
        assert absent_release_topic.json()["error"]["code"] == "topic_not_found"
        unknown_release = client.get(f"/api/v1/curriculum/releases/{uuid4()}/topics/T")
        assert unknown_release.status_code == 404


def test_readiness_reuses_engine_and_is_scoped_to_release_and_learner(api_context):
    app, ctx = api_context
    with LocalASGIClient(app) as client:
        first = client.get(
            f"/api/v1/curriculum/releases/{ctx['release_id']}/learners/{ctx['learner_id']}/topics/T/readiness"
        )
        assert first.status_code == 200
        body = first.json()
        assert body["readiness"] == "unknown"
        assert body["groups"][0]["unknown_topic_ids"] == ["A"]
        assert body["groups"][1]["unknown_topic_ids"] == ["ALT"]
        assert body["has_satisfied_group"] is False

        unknown_learner = client.get(
            f"/api/v1/curriculum/releases/{ctx['release_id']}/learners/9999/topics/T/readiness"
        )
        assert unknown_learner.status_code == 404
        assert unknown_learner.json()["error"]["code"] == "learner_not_found"
        release_without_dependency = client.get(
            f"/api/v1/curriculum/releases/{ctx['second_release_id']}/learners/{ctx['learner_id']}/topics/T/readiness"
        )
        assert release_without_dependency.json()["readiness"] == "ready"


def test_progress_independent_updates_before_images_and_clear_preserves_evidence(api_context, engine):
    app, ctx = api_context
    prefix = f"/api/v1/curriculum/releases/{ctx['release_id']}/learners/{ctx['learner_id']}/progress/T"
    with LocalASGIClient(app) as client:
        missing = client.get(prefix)
        assert missing.status_code == 200
        assert missing.json() == {"progress": None}
        with Session(engine) as session:
            assert session.get(LearnerProgress, (ctx["learner_id"], "T")) is None

        created = client.patch(prefix, json={"progress_status": "Practicing"})
        assert created.status_code == 200
        assert created.json()["progress"]["progress_status"] == "Practicing"
        assert created.json()["progress"]["confidence"] is None

        confidence = client.patch(prefix, json={"confidence": 4})
        assert confidence.status_code == 200
        assert confidence.json()["progress"]["progress_status"] == "Practicing"
        assert confidence.json()["progress"]["confidence"] == 4

        clear_status = client.patch(prefix, json={"progress_status": None})
        assert clear_status.status_code == 200
        assert clear_status.json()["progress"]["progress_status"] is None
        assert clear_status.json()["progress"]["confidence"] == 4

        with Session(engine) as session:
            evidence = LearnerEvidence(
                learner_id=ctx["learner_id"], evidence_id="EV-API", evidence_type="note", description="Keep me", source_payload={}
            )
            session.add(evidence)
            previous_history = session.scalar(
                select(ProgressHistory).where(
                    ProgressHistory.learner_id == ctx["learner_id"],
                    ProgressHistory.topic_id == "T",
                ).order_by(ProgressHistory.id.desc())
            )
            session.add(
                ProgressHistoryEvidence(
                    history_id=previous_history.id,
                    learner_id=ctx["learner_id"],
                    topic_id="T",
                    evidence_id="EV-API",
                )
            )
            session.commit()

        deleted = client.delete(prefix)
        assert deleted.status_code == 204
        assert client.get(prefix).json() == {"progress": None}
        with Session(engine) as session:
            history = session.scalars(
                select(ProgressHistory)
                .where(ProgressHistory.learner_id == ctx["learner_id"], ProgressHistory.topic_id == "T")
                .order_by(ProgressHistory.id)
            ).all()
            assert len(history) == 4
            assert history[0].event_type == "api_before_change_unassessed"
            assert history[0].progress_status is None and history[0].confidence is None
            assert history[1].progress_status == "Practicing" and history[1].confidence is None
            assert history[2].progress_status == "Practicing" and history[2].confidence == 4
            assert history[3].progress_status is None and history[3].confidence == 4
            assert session.get(LearnerProgress, (ctx["learner_id"], "T")) is None
            assert session.get(LearnerEvidence, (ctx["learner_id"], "EV-API")) is not None
            assert session.scalar(select(func.count()).select_from(ProgressHistoryEvidence)) == 1


def test_progress_validation_and_scoping_errors_are_normalized(api_context):
    app, ctx = api_context
    with LocalASGIClient(app) as client:
        base = f"/api/v1/curriculum/releases/{ctx['release_id']}/learners/{ctx['learner_id']}/progress"
        invalid_status = client.patch(f"{base}/T", json={"progress_status": "Mastered"})
        assert invalid_status.status_code == 422
        assert invalid_status.json()["error"]["code"] == "request_validation_error"
        empty = client.patch(f"{base}/T", json={})
        assert empty.status_code == 422
        assert empty.json()["error"]["code"] == "request_validation_error"
        bad_confidence = client.patch(f"{base}/T", json={"confidence": 6})
        assert bad_confidence.status_code == 422

        create = client.patch(f"{base}/T", json={"confidence": 3})
        assert create.status_code == 200
        clear_both_patch = client.patch(f"{base}/T", json={"confidence": None})
        assert clear_both_patch.status_code == 422
        assert clear_both_patch.json()["error"]["code"] == "assessment_required"
        other_learner = client.get(
            f"/api/v1/curriculum/releases/{ctx['release_id']}/learners/{ctx['second_learner_id']}/progress/T"
        )
        assert other_learner.status_code == 200 and other_learner.json() == {"progress": None}
        outside_release = client.get(
            f"/api/v1/curriculum/releases/{ctx['second_release_id']}/learners/{ctx['learner_id']}/progress/UNASSESSED"
        )
        assert outside_release.status_code == 404


def test_progress_history_and_current_state_roll_back_together(api_context, engine):
    app, ctx = api_context
    prefix = f"/api/v1/curriculum/releases/{ctx['release_id']}/learners/{ctx['learner_id']}/progress/T"
    with LocalASGIClient(app) as client:
        first = client.patch(prefix, json={"progress_status": "Learning"})
        assert first.status_code == 200
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TRIGGER fail_progress_update BEFORE UPDATE OF confidence ON learner_progress "
                "BEGIN SELECT RAISE(ABORT, 'forced update failure'); END"
            )

        failed = client.patch(prefix, json={"confidence": 5})
        assert failed.status_code == 500
        assert failed.json()["error"]["code"] == "internal_error"
        assert "forced update failure" not in failed.body.decode("utf-8")
        with Session(engine) as session:
            current = session.get(LearnerProgress, (ctx["learner_id"], "T"))
            assert current.progress_status == "Learning"
            assert current.confidence is None
            assert session.scalar(
                select(func.count()).select_from(ProgressHistory).where(
                    ProgressHistory.learner_id == ctx["learner_id"], ProgressHistory.topic_id == "T"
                )
            ) == 1


@requires_curriculum_package
def test_actual_v3_package_exposes_release_and_topics_through_api(engine):
    imported = import_curriculum_package(PACKAGE_PATH, make_session_factory(engine))
    app = create_app(engine=engine)
    with LocalASGIClient(app) as client:
        releases = client.get("/api/v1/curriculum/releases").json()["items"]
        assert len(releases) == 1
        release = releases[0]
        assert release["curriculum_version"] == "3.0.0"
        assert release["schema_version"] == "1.0.0-draft"
        assert release["release_id"]
        assert "id" not in release

        root = f"/api/v1/curriculum/releases/{release['release_id']}"
        overview = client.get(root).json()
        assert overview["topic_count"] == 334
        assert len(client.get(f"{root}/tracks").json()["items"]) == 5
        assert len(client.get(f"{root}/phases").json()["items"]) == 17
        first_page = client.get(f"{root}/topics?limit=20").json()
        assert len(first_page["items"]) == 20
        assert first_page["next_cursor"]
        topic = client.get(f"{root}/topics/CS-001").json()
        assert topic["id"] == "CS-001"
        assert len(topic["objectives"]) == 3

        selected = client.put("/api/v1/curriculum/active-release", json={"release_id": release["release_id"]})
        assert selected.status_code == 200
        assert selected.json()["release_id"] == release["release_id"]
        assert imported.release_id > 0  # Internal import report ID is not serialized by the HTTP API.
