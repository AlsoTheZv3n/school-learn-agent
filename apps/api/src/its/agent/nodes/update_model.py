"""update_model node (AG-2): the model updates, not the agent (P3).

Writes the attempt and updates learner_state via record_attempt — but only cements a
result when grader confidence is high enough (>= 0.9). Low-confidence grades (e.g.
open history answers) are left for teacher review (P6), never auto-committed.
"""

import uuid
from collections.abc import Callable

from sqlalchemy import text
from sqlalchemy.orm import Session

from its.agent.state import TutorState
from its.db.models import Attempt
from its.learner_model.tracing import record_attempt

_CEMENT_CONFIDENCE = 0.9


def _resolve_skill_id(session: Session, subject_key: str, skill_key: str):
    return session.execute(
        text(
            "SELECT s.id FROM skills s JOIN subjects sub ON sub.id = s.subject_id "
            "WHERE s.key = :k AND sub.key = :subj"
        ),
        {"k": skill_key, "subj": subject_key},
    ).scalar()


def make_update_model_node(session: Session) -> Callable:
    def update_model_node(state: TutorState) -> dict:
        if not state.grade:
            return {}
        if state.grade["confidence"] < _CEMENT_CONFIDENCE:
            return {}  # not cemented -> teacher review (P6)
        skill_id = _resolve_skill_id(session, state.subject_key, state.skill_key)
        if skill_id is None:
            return {}
        sid = uuid.UUID(state.student_id) if isinstance(state.student_id, str) else state.student_id
        session.add(
            Attempt(
                student_id=sid,
                skill_id=skill_id,
                item_ref=state.item_ref or "",
                is_correct=bool(state.grade["correct"]),
                raw_answer=state.answer,
            )
        )
        ls = record_attempt(session, sid, skill_id, bool(state.grade["correct"]))
        return {"mastery": ls.mastery}

    return update_model_node
