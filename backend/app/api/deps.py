"""FastAPI request dependencies."""

from __future__ import annotations

from collections.abc import Generator

from fastapi import Request
from sqlalchemy.orm import Session


def get_session(request: Request) -> Generator[Session, None, None]:
    factory = request.app.state.session_factory
    with factory() as session:
        yield session
