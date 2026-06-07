"""external_id on students + classes (idempotent production import)

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-07

Adds a nullable, unique external_id to students and classes so the production
roster import (PROD-1) can upsert by a stable external key instead of blind insert.
Nullable: mock-seeded rows have no external_id (and Postgres allows many NULLs in a
UNIQUE column, so they never conflict).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("students", sa.Column("external_id", sa.Text(), nullable=True))
    op.add_column("classes", sa.Column("external_id", sa.Text(), nullable=True))
    op.create_unique_constraint("uq_students_external_id", "students", ["external_id"])
    op.create_unique_constraint("uq_classes_external_id", "classes", ["external_id"])


def downgrade() -> None:
    op.drop_constraint("uq_students_external_id", "students", type_="unique")
    op.drop_constraint("uq_classes_external_id", "classes", type_="unique")
    op.drop_column("students", "external_id")
    op.drop_column("classes", "external_id")
