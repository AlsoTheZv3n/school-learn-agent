"""Tracing service (LM-2): apply a BKT update to learner_state from one attempt.

Always write through this service (not directly into learner_state) so mastery and
uncertainty stay consistent (P3: the model updates, not the agent). `uncertainty`
is a coarse 1/(attempts+1) measure for the open learner model (P5).
"""

import uuid

from sqlalchemy.orm import Session

from its.db.models import LearnerState
from its.learner_model.bkt import BKTParams, update


def record_attempt(
    session: Session,
    student_id: str | uuid.UUID,
    skill_id: str | uuid.UUID,
    correct: bool,
    params: BKTParams | None = None,
) -> LearnerState:
    p = params or BKTParams()
    state = session.get(LearnerState, {"student_id": student_id, "skill_id": skill_id})
    if state is None:
        state = LearnerState(
            student_id=student_id,
            skill_id=skill_id,
            mastery=p.p_init,
            uncertainty=1.0,
            attempts_count=0,
        )
        session.add(state)
    state.mastery = update(state.mastery, correct, p)
    state.attempts_count += 1
    state.uncertainty = 1.0 / (state.attempts_count + 1)
    session.flush()
    return state
