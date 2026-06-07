"""seed — small math skill graph (demo)

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-07

A tiny, idempotent demo skill graph (DB-4): subject 'math' with three skills and
prerequisite edges (linear-equations -> complete-the-square -> quadratic-formula).
Real/bulk data comes from the seeder (docs/11). Inserts are ON CONFLICT DO NOTHING.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SKILLS = [
    ("linear-equations", "Lineare Gleichungen", 8),
    ("complete-the-square", "Quadratische Ergänzung", 9),
    ("quadratic-formula", "Quadratische Lösungsformel", 9),
]
_EDGES = [
    ("linear-equations", "complete-the-square"),
    ("complete-the-square", "quadratic-formula"),
]


def upgrade() -> None:
    op.execute(
        "INSERT INTO subjects (key, name) VALUES ('math', 'Mathematik') "
        "ON CONFLICT (key) DO NOTHING"
    )
    for key, name, grade in _SKILLS:
        op.execute(
            "INSERT INTO skills (subject_id, key, name, grade_level) "
            "SELECT s.id, '{key}', '{name}', {grade} FROM subjects s WHERE s.key='math' "
            "ON CONFLICT (subject_id, key) DO NOTHING".format(key=key, name=name, grade=grade)
        )
    for frm, to in _EDGES:
        op.execute(
            "INSERT INTO skill_edges (from_skill, to_skill, kind) "
            "SELECT f.id, t.id, 'prerequisite' "
            "FROM skills f, skills t "
            "WHERE f.key='{frm}' AND t.key='{to}' "
            "ON CONFLICT (from_skill, to_skill, kind) DO NOTHING".format(frm=frm, to=to)
        )


def downgrade() -> None:
    op.execute(
        "DELETE FROM skill_edges WHERE from_skill IN (SELECT id FROM skills WHERE key IN "
        "('linear-equations','complete-the-square','quadratic-formula'))"
    )
    op.execute(
        "DELETE FROM skills WHERE key IN "
        "('linear-equations','complete-the-square','quadratic-formula')"
    )
    op.execute("DELETE FROM subjects WHERE key='math'")
