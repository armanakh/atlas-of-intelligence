"""Initialize or upgrade the local database to the latest Alembic revision."""

from pathlib import Path

from alembic import command
from alembic.config import Config

from app.db.database import database_url, ensure_database_directory


def initialize_database(url: str | None = None) -> None:
    resolved = url or database_url()
    ensure_database_directory(resolved)
    root = Path(__file__).resolve().parents[3]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "backend" / "migrations"))
    config.set_main_option("sqlalchemy.url", resolved.replace("%", "%%"))
    command.upgrade(config, "head")


if __name__ == "__main__":
    initialize_database()
    print(f"Database is initialized at {database_url()}")
