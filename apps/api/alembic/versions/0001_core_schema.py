"""core schema — all tables for the three retrieval modes + HNSW index

Revision ID: 0001
Revises:
Create Date: 2026-06-07

Creates the full relational schema (docs/03-database.md). Tables are created in
FK-dependency order. The content_embeddings.embedding column uses pgvector with a
1024-dim placeholder (open question E2 #2) and an HNSW cosine index for semantic search.
Requires the `vector` and `uuid-ossp` extensions (created by infra/init on first
container start; in CI created explicitly before migrate).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UUID = sa.dialects.postgresql.UUID(as_uuid=True)
_PK_DEFAULT = sa.text("uuid_generate_v4()")
_NOW = sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "students",
        sa.Column("id", _UUID, primary_key=True, server_default=_PK_DEFAULT),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("grade_level", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_NOW),
    )
    op.create_table(
        "teachers",
        sa.Column("id", _UUID, primary_key=True, server_default=_PK_DEFAULT),
        sa.Column("display_name", sa.Text(), nullable=False),
    )
    op.create_table(
        "classes",
        sa.Column("id", _UUID, primary_key=True, server_default=_PK_DEFAULT),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("teacher_id", _UUID, sa.ForeignKey("teachers.id")),
    )
    op.create_table(
        "enrollments",
        sa.Column(
            "student_id", _UUID, sa.ForeignKey("students.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column(
            "class_id", _UUID, sa.ForeignKey("classes.id", ondelete="CASCADE"), primary_key=True
        ),
    )
    op.create_table(
        "subjects",
        sa.Column("id", _UUID, primary_key=True, server_default=_PK_DEFAULT),
        sa.Column("key", sa.Text(), nullable=False, unique=True),
        sa.Column("name", sa.Text(), nullable=False),
    )
    op.create_table(
        "skills",
        sa.Column("id", _UUID, primary_key=True, server_default=_PK_DEFAULT),
        sa.Column("subject_id", _UUID, sa.ForeignKey("subjects.id")),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("grade_level", sa.Integer(), nullable=False),
        sa.UniqueConstraint("subject_id", "key", name="uq_skills_subject_key"),
    )
    op.create_table(
        "skill_edges",
        sa.Column(
            "from_skill", _UUID, sa.ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column(
            "to_skill", _UUID, sa.ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column(
            "kind", sa.Text(), primary_key=True, nullable=False, server_default=sa.text("'prerequisite'")
        ),
    )
    op.create_table(
        "content_notes",
        sa.Column("id", _UUID, primary_key=True, server_default=_PK_DEFAULT),
        sa.Column("skill_id", _UUID, sa.ForeignKey("skills.id")),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("prose", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_NOW),
    )
    op.create_table(
        "content_embeddings",
        sa.Column("id", _UUID, primary_key=True, server_default=_PK_DEFAULT),
        sa.Column(
            "note_id", _UUID, sa.ForeignKey("content_notes.id", ondelete="CASCADE")
        ),
        sa.Column("chunk", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1024), nullable=False),  # EMBEDDING_DIM (E2 #2)
        sa.Column("sidecar_query", sa.Text()),
    )
    op.create_table(
        "attempts",
        sa.Column("id", _UUID, primary_key=True, server_default=_PK_DEFAULT),
        sa.Column(
            "student_id", _UUID, sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("skill_id", _UUID, sa.ForeignKey("skills.id"), nullable=False),
        sa.Column("item_ref", sa.Text(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("raw_answer", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_NOW),
    )
    op.create_index("ix_attempts_student_skill_time", "attempts", ["student_id", "skill_id", "created_at"])
    op.create_table(
        "learner_state",
        sa.Column(
            "student_id", _UUID, sa.ForeignKey("students.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("skill_id", _UUID, sa.ForeignKey("skills.id"), primary_key=True),
        sa.Column("mastery", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("uncertainty", sa.Float(), nullable=False, server_default=sa.text("1.0")),
        sa.Column("attempts_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=_NOW),
    )
    op.create_table(
        "teacher_notes",
        sa.Column("id", _UUID, primary_key=True, server_default=_PK_DEFAULT),
        sa.Column(
            "student_id", _UUID, sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("teacher_id", _UUID, sa.ForeignKey("teachers.id"), nullable=False),
        sa.Column("skill_id", _UUID, sa.ForeignKey("skills.id")),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("override_mastery", sa.Float()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_NOW),
    )
    # HNSW cosine index for semantic similarity (docs/03 §3).
    op.execute(
        "CREATE INDEX ix_content_embeddings_hnsw ON content_embeddings "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_content_embeddings_hnsw")
    op.drop_table("teacher_notes")
    op.drop_table("learner_state")
    op.drop_index("ix_attempts_student_skill_time", table_name="attempts")
    op.drop_table("attempts")
    op.drop_table("content_embeddings")
    op.drop_table("content_notes")
    op.drop_table("skill_edges")
    op.drop_table("skills")
    op.drop_table("subjects")
    op.drop_table("enrollments")
    op.drop_table("classes")
    op.drop_table("teachers")
    op.drop_table("students")
