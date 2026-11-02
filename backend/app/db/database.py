"""SQLite engine/session helpers with foreign-key enforcement enabled."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker


DEFAULT_DATABASE_URL = "sqlite:///./data/curriculum.db"


def database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def make_engine(url: str | None = None, *, echo: bool = False) -> Engine:
    resolved = url or database_url()
    connect_args = {"check_same_thread": False} if resolved.startswith("sqlite") else {}
    engine = create_engine(resolved, echo=echo, connect_args=connect_args)

    if resolved.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def ensure_database_directory(url: str) -> None:
    """Create the parent directory for the default relative SQLite file, if needed."""
    prefix = "sqlite:///"
    if url.startswith(prefix) and not url.startswith("sqlite:////") and url != "sqlite:///:memory:":
        path = Path(url[len(prefix):])
        if path.parent != Path("."):
            path.parent.mkdir(parents=True, exist_ok=True)
