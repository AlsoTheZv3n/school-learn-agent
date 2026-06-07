"""Test fixtures (TST-1, set up early to support the SAF-4 safety tests).

The safety tests run against REAL Postgres with RLS enabled — against SQLite the
most important property (row isolation) would not be exercised at all (docs/10 §1).

`role_conn` is a deliberate mirror of db/session.py:scoped_session — it switches
the Postgres role and sets the per-request scope via set_config(..., is_local=true),
exactly the mechanism the RLS policies rely on.
"""

import os
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import Connection

TEST_DB_URL = os.environ["DATABASE_URL"]  # CI: Postgres service; local: docker on 5433


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    eng = create_engine(TEST_DB_URL, pool_pre_ping=True)
    # Apply migrations incl. rls.sql against the test DB (idempotent if already at head).
    from alembic import command
    from alembic.config import Config

    cfg = Config("alembic.ini")  # pytest runs from apps/api (cwd)
    command.upgrade(cfg, "head")
    yield eng
    eng.dispose()


@contextmanager
def role_conn(
    eng: Engine, role: str, *, student_id=None, teacher_id=None
) -> Iterator[Connection]:
    """Open a connection switched into `role` with optional scope (transaction-local)."""
    conn = eng.connect()
    trans = conn.begin()
    try:
        conn.execute(text("SELECT set_config('role', :r, true)"), {"r": role})
        if student_id is not None:
            conn.execute(
                text("SELECT set_config('app.current_student_id', :v, true)"),
                {"v": str(student_id)},
            )
        if teacher_id is not None:
            conn.execute(
                text("SELECT set_config('app.current_teacher_id', :v, true)"),
                {"v": str(teacher_id)},
            )
        yield conn
    finally:
        trans.rollback()  # clears local role/scope + any writes
        conn.close()


@pytest.fixture
def as_role(engine: Engine):
    """Factory: `with as_role("its_student", student_id=a) as conn: ...`."""

    @contextmanager
    def _as(role: str, *, student_id=None, teacher_id=None) -> Iterator[Connection]:
        with role_conn(engine, role, student_id=student_id, teacher_id=teacher_id) as conn:
            yield conn

    return _as


class DBFactory:
    """Opens role-scoped sessions — a test mirror of db/session.py:scoped_session (TST-1).

    Lets a test run exactly under its_student / its_teacher / its_admin so the RLS
    policies are exercised through the same role + set_config mechanism as production.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def as_student(self, student_id=None):
        return role_conn(self._engine, "its_student", student_id=student_id)

    def as_teacher(self, teacher_id):
        return role_conn(self._engine, "its_teacher", teacher_id=teacher_id)

    def as_admin(self):
        return role_conn(self._engine, "its_admin")


@pytest.fixture
def db_factory(engine: Engine) -> DBFactory:
    return DBFactory(engine)


@pytest.fixture
def seeded_rls(engine: Engine):
    """Commit an isolated RLS scenario as the owner role, yield ids, then clean up.

    Owner (`its`) bypasses RLS (no FORCE), so this setup writes freely; the tests
    then switch to its_student/its_teacher where RLS applies. Data is committed so
    the separate role-scoped connections can see it.

    Layout: teacher T owns class C; student A is enrolled in C, student B is not.
    A has 2 attempts, B has 1 attempt, both on the test skill; both have a state row.
    """
    sfx = uuid.uuid4().hex[:8]
    ids = {
        "subject": uuid.uuid4(),
        "skill": uuid.uuid4(),
        "teacher": uuid.uuid4(),
        "klass": uuid.uuid4(),
        "a": uuid.uuid4(),
        "b": uuid.uuid4(),
    }
    with engine.begin() as c:
        c.execute(
            text("INSERT INTO subjects (id, key, name) VALUES (:id, :k, 'Test')"),
            {"id": ids["subject"], "k": f"rlssub-{sfx}"},
        )
        c.execute(
            text(
                "INSERT INTO skills (id, subject_id, key, name, grade_level) "
                "VALUES (:id, :sub, :k, 'Test Skill', 9)"
            ),
            {"id": ids["skill"], "sub": ids["subject"], "k": f"rlsskill-{sfx}"},
        )
        c.execute(
            text("INSERT INTO teachers (id, display_name) VALUES (:id, 'T')"),
            {"id": ids["teacher"]},
        )
        c.execute(
            text("INSERT INTO classes (id, name, teacher_id) VALUES (:id, 'C', :t)"),
            {"id": ids["klass"], "t": ids["teacher"]},
        )
        for who, name in [("a", "A"), ("b", "B")]:
            c.execute(
                text("INSERT INTO students (id, display_name, grade_level) VALUES (:id, :n, 9)"),
                {"id": ids[who], "n": name},
            )
            c.execute(
                text(
                    "INSERT INTO learner_state (student_id, skill_id, mastery, uncertainty, attempts_count) "
                    "VALUES (:s, :sk, 0.5, 0.3, 1)"
                ),
                {"s": ids[who], "sk": ids["skill"]},
            )
        # Only A is enrolled in the teacher's class.
        c.execute(
            text("INSERT INTO enrollments (student_id, class_id) VALUES (:s, :c)"),
            {"s": ids["a"], "c": ids["klass"]},
        )
        # A: 2 attempts, B: 1 attempt.
        for i in range(2):
            c.execute(
                text(
                    "INSERT INTO attempts (student_id, skill_id, item_ref, is_correct) "
                    "VALUES (:s, :sk, :ref, true)"
                ),
                {"s": ids["a"], "sk": ids["skill"], "ref": f"a-{i}"},
            )
        c.execute(
            text(
                "INSERT INTO attempts (student_id, skill_id, item_ref, is_correct) "
                "VALUES (:s, :sk, 'b-0', false)"
            ),
            {"s": ids["b"], "sk": ids["skill"]},
        )
    yield ids
    # Teardown (owner): delete students (cascades attempts/state/enrollments), then rest.
    with engine.begin() as c:
        c.execute(
            text("DELETE FROM students WHERE id = ANY(:ids)"),
            {"ids": [ids["a"], ids["b"]]},
        )
        c.execute(text("DELETE FROM classes WHERE id = :id"), {"id": ids["klass"]})
        c.execute(text("DELETE FROM teachers WHERE id = :id"), {"id": ids["teacher"]})
        c.execute(text("DELETE FROM skills WHERE id = :id"), {"id": ids["skill"]})
        c.execute(text("DELETE FROM subjects WHERE id = :id"), {"id": ids["subject"]})
