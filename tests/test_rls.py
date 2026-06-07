"""SAF-4 — RLS isolation proof (CI-blocking). Runs against real Postgres + RLS.

Proves the two properties whose silent breakage would leak children's data:
a student cannot read another student's rows, an unscoped student session sees
nothing (fail-closed), and a teacher sees only their own class's students.
"""

from sqlalchemy import text


def test_student_sees_only_own_attempts(as_role, seeded_rls) -> None:
    a, b = seeded_rls["a"], seeded_rls["b"]
    with as_role("its_student", student_id=a) as c:
        own = c.execute(text("SELECT count(*) FROM attempts")).scalar()
        other = c.execute(
            text("SELECT count(*) FROM attempts WHERE student_id = :b"), {"b": b}
        ).scalar()
    assert own == 2  # A's own attempts visible
    assert other == 0  # B's attempts are NOT visible to A


def test_student_sees_only_own_learner_state(as_role, seeded_rls) -> None:
    a, b = seeded_rls["a"], seeded_rls["b"]
    with as_role("its_student", student_id=a) as c:
        own = c.execute(text("SELECT count(*) FROM learner_state")).scalar()
        other = c.execute(
            text("SELECT count(*) FROM learner_state WHERE student_id = :b"), {"b": b}
        ).scalar()
    assert own == 1
    assert other == 0


def test_unset_scope_returns_no_rows(as_role, seeded_rls) -> None:
    # Student role without app.current_student_id -> fail-closed (0 rows, not all rows).
    with as_role("its_student") as c:
        n = c.execute(text("SELECT count(*) FROM attempts")).scalar()
    assert n == 0


def test_teacher_sees_class_student_not_outsiders(as_role, seeded_rls) -> None:
    a, b, t = seeded_rls["a"], seeded_rls["b"], seeded_rls["teacher"]
    with as_role("its_teacher", teacher_id=t) as c:
        a_rows = c.execute(
            text("SELECT count(*) FROM attempts WHERE student_id = :a"), {"a": a}
        ).scalar()
        b_rows = c.execute(
            text("SELECT count(*) FROM attempts WHERE student_id = :b"), {"b": b}
        ).scalar()
    assert a_rows == 2  # A is enrolled in the teacher's class -> visible
    assert b_rows == 0  # B is not in the teacher's class -> invisible
