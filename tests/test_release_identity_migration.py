from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.db.database import make_engine


ROOT = Path(__file__).resolve().parents[1]
BASE_REVISION = "24d9c72cc7f1"
HEAD_REVISION = "8bb934a110d2"


def alembic_config(database_url: str) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "backend" / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def test_release_identity_migration_backfills_without_selecting_and_downgrades(tmp_path):
    db_path = tmp_path / "release-identity.db"
    url = f"sqlite:///{db_path}"
    config = alembic_config(url)
    command.upgrade(config, BASE_REVISION)

    engine = make_engine(url)
    with engine.begin() as connection:
        result = connection.execute(
            text(
                "INSERT INTO curriculum_release "
                "(curriculum_version, schema_version, release_status, source_digest, source_payload, dependency_payload) "
                "VALUES (:version, :schema, :status, :digest, :source, :dependency)"
            ),
            {
                "version": "3.0.0",
                "schema": "1.0.0-draft",
                "status": "curriculum_release_candidate",
                "digest": "migration-test",
                "source": "{}",
                "dependency": "{}",
            },
        )
        release_id = result.lastrowid
        connection.execute(text("INSERT INTO topic_identity (topic_id) VALUES ('MIGRATION-TOPIC')"))
        connection.execute(
            text(
                "INSERT INTO topic_version (release_id, topic_id, title, source_payload) "
                "VALUES (:release_id, 'MIGRATION-TOPIC', 'Migration topic', '{}')"
            ),
            {"release_id": release_id},
        )
    command.upgrade(config, HEAD_REVISION)

    with engine.connect() as connection:
        release = connection.execute(
            text("SELECT public_id, release_status FROM curriculum_release WHERE curriculum_version = '3.0.0'")
        ).one()
        assert len(release.public_id) == 36
        assert release.release_status == "curriculum_release_candidate"
        assert connection.scalar(text("SELECT count(*) FROM active_curriculum_release")) == 0
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO active_curriculum_release (singleton_id, release_id) VALUES (1, 1)"))
    with pytest.raises(IntegrityError, match="public release id is immutable"):
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE curriculum_release SET public_id = :new_id WHERE curriculum_version = '3.0.0'"),
                {"new_id": "00000000-0000-0000-0000-000000000000"},
            )
    with pytest.raises(IntegrityError, match="public release id is required"):
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE curriculum_release SET public_id = NULL WHERE curriculum_version = '3.0.0'")
            )
    assert "active_curriculum_release" in inspect(engine).get_table_names()

    command.downgrade(config, BASE_REVISION)
    inspector = inspect(engine)
    assert "active_curriculum_release" not in inspector.get_table_names()
    assert "public_id" not in {column["name"] for column in inspector.get_columns("curriculum_release")}
    engine.dispose()
