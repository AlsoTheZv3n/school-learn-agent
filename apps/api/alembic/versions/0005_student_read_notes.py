"""grant its_student SELECT on teacher_notes (pairs with student_notes_about_self policy)

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-07

The student_notes_about_self RLS policy (0002) lets a student read notes about
themselves, but the table-level GRANT was missing — a policy without a GRANT is
still denied. This adds the read grant; the policy keeps it to own rows.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("GRANT SELECT ON teacher_notes TO its_student")


def downgrade() -> None:
    op.execute("REVOKE SELECT ON teacher_notes FROM its_student")
