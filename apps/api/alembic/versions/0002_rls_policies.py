"""rls policies — roles, grants, row-level security (safety-critical)

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-07

Executes src/its/safety/rls.sql (the canonical, versioned RLS source). The SQL is
read from disk at migration time; it is versioned alongside this migration, so a
given commit is reproducible. See docs/04-safety.md.
"""

from collections.abc import Sequence
from pathlib import Path

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# alembic/versions/0002_*.py -> parents[2] == apps/api
_RLS_SQL = Path(__file__).parents[2] / "src" / "its" / "safety" / "rls.sql"

_PERSON_TABLES = ("attempts", "learner_state", "teacher_notes", "enrollments")


def upgrade() -> None:
    op.execute(_RLS_SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    # Drop policies and disable RLS; keep the shared roles (other DBs/migrations may use them).
    for policy, table in [
        ("student_attempts_self", "attempts"),
        ("teacher_attempts_in_class", "attempts"),
        ("student_state_self", "learner_state"),
        ("teacher_state_in_class", "learner_state"),
        ("student_notes_about_self", "teacher_notes"),
        ("teacher_notes_rw", "teacher_notes"),
        ("student_enrollment_self", "enrollments"),
        ("teacher_enrollment_in_class", "enrollments"),
    ]:
        op.execute(f'DROP POLICY IF EXISTS {policy} ON {table}')
    for table in _PERSON_TABLES:
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
