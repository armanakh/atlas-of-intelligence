from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.db.database import make_engine
from app.db.models import Base


@pytest.fixture
def engine(tmp_path: Path):
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine):
    with Session(engine) as session:
        yield session
