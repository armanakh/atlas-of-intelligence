"""Read-only local learner resolution operations."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import APIError
from app.db.models import Learner
from app.schemas.learner_api import LearnerResponse


def get_current_learner(session: Session) -> LearnerResponse:
    """Return the sole existing learner, or explain why one cannot be resolved."""
    # Read the candidates in one statement so the decision is based on one
    # database view and never depends on which learner happens to sort first.
    learners = session.scalars(select(Learner).order_by(Learner.id)).all()
    if not learners:
        raise APIError(
            404,
            "current_learner_not_found",
            "No local learner exists",
            {"learner_count": 0},
        )
    if len(learners) > 1:
        raise APIError(
            409,
            "current_learner_ambiguous",
            "A current learner cannot be resolved because multiple local learners exist",
            {"learner_count": len(learners)},
        )

    learner = learners[0]
    return LearnerResponse(learner_id=learner.id, display_name=learner.display_name)
