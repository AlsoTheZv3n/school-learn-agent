"""Agent loop integration (AG, TST-3): a full ANSWER turn end-to-end vs the test DB.

Operationalizes the principles: assess is deterministic (confidence 1.0, P2) and the
LEARNER MODEL changes — not the agent (P3). Runs inside a real scoped_session (RLS).
"""

import uuid

import pytest
from sqlalchemy import text

from its.agent.graph import run_turn
from its.agent.state import Intent, TutorState
from its.auth.deps import Principal
from its.auth.roles import Role
from its.db.session import scoped_session


@pytest.fixture
def agent_student(engine):
    sid = uuid.uuid4()
    with engine.begin() as c:
        c.execute(
            text("INSERT INTO students (id, display_name, grade_level) VALUES (:id, 'AgentStud', 9)"),
            {"id": sid},
        )
    yield sid
    with engine.begin() as c:
        c.execute(text("DELETE FROM students WHERE id = :id"), {"id": sid})


def _principal(sid) -> Principal:
    return Principal(user_id=str(sid), role=Role.STUDENT, student_id=str(sid))


def test_answer_turn_grades_curated_and_updates_model(agent_student) -> None:
    state = TutorState(
        student_id=str(agent_student),
        subject_key="math",
        skill_key="complete-the-square",
        intent=Intent.ANSWER,
        answer="x^2 + 2*x + 1",
        item_ref="expand-x-plus-1-squared",
    )
    with scoped_session(_principal(agent_student)) as s:
        result = run_turn(state, session=s)

    assert result.grade is not None
    assert result.grade["confidence"] == 1.0  # curated, deterministic (P2)
    assert result.grade["correct"] is True
    assert result.mastery is not None  # learner model updated (P3)
    assert result.mastery > 0.2  # rose above p_init after a correct answer


def test_wrong_answer_is_graded_but_still_updates_model(agent_student) -> None:
    state = TutorState(
        student_id=str(agent_student),
        subject_key="math",
        skill_key="complete-the-square",
        intent=Intent.ANSWER,
        answer="x^2 + 1",  # wrong
        item_ref="expand-x-plus-1-squared",
    )
    with scoped_session(_principal(agent_student)) as s:
        result = run_turn(state, session=s)
    assert result.grade["correct"] is False
    assert result.grade["confidence"] == 1.0
    assert result.mastery is not None  # a wrong attempt still updates the model


def test_explain_turn_is_generative_not_assessed(agent_student) -> None:
    state = TutorState(
        student_id=str(agent_student),
        subject_key="math",
        skill_key="complete-the-square",
        intent=Intent.EXPLAIN,
    )
    with scoped_session(_principal(agent_student)) as s:
        result = run_turn(state, session=s)
    assert result.explanation
    assert result.grade is None  # explain path does not assess (P2 separation)
