import pytest
from pydantic import ValidationError

from app.schemas.curriculum import CurriculumImportInput


def test_import_schema_preserves_unknown_fields_and_omitted_optional_metadata():
    document = CurriculumImportInput.model_validate(
        {
            "curriculum_version": "3.0.0",
            "schema_version": "1.0.0-draft",
            "tracks": [],
            "phases": [],
            "topics": [
                {
                    "id": "CS-001",
                    "title": "Topic",
                    "phase_id": "PH01",
                    "track_ids": ["TR-CS"],
                    "future_extension": {"preserve": ["as supplied"]},
                }
            ],
        }
    )
    topic = document.topics[0]
    preserved = topic.model_dump(exclude_unset=True)
    assert preserved["future_extension"] == {"preserve": ["as supplied"]}
    assert "prerequisite_groups" not in preserved
    assert topic.prerequisite_groups is None


def test_import_schema_keeps_empty_prerequisites_distinct_from_empty_group():
    base = {
        "curriculum_version": "3.0.0",
        "schema_version": "1.0.0-draft",
        "topics": [
            {"id": "A", "title": "A", "phase_id": "P", "track_ids": [], "prerequisite_groups": []}
        ],
    }
    assert CurriculumImportInput.model_validate(base).topics[0].prerequisite_groups == []
    base["topics"][0]["prerequisite_groups"] = [{"requires_all": []}]
    with pytest.raises(ValidationError):
        CurriculumImportInput.model_validate(base)
