"""SQLAlchemy 2.0 models for all three retrieval modes out of one database.

PII minimization (P4): `students` carries only what is needed (display_name,
grade_level) — no free-text profile. Identifying data never leaves the DB raw.

The embedding dimension is centralized here (open question E2 #2). It currently
matches the schema placeholder (1024); the final value is fixed together with the
embedding-model decision (E4/E5). Changing it requires a schema migration + re-embed.
"""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

EMBEDDING_DIM = 1024


class Base(DeclarativeBase):
    pass


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("uuid_generate_v4()"),
    )


class Student(Base):
    __tablename__ = "students"
    id: Mapped[uuid.UUID] = _uuid_pk()
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    grade_level: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Teacher(Base):
    __tablename__ = "teachers"
    id: Mapped[uuid.UUID] = _uuid_pk()
    display_name: Mapped[str] = mapped_column(String, nullable=False)


class Class(Base):
    __tablename__ = "classes"
    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String, nullable=False)
    teacher_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("teachers.id"))

    teacher: Mapped["Teacher | None"] = relationship()


class Enrollment(Base):
    __tablename__ = "enrollments"
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), primary_key=True
    )
    class_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("classes.id", ondelete="CASCADE"), primary_key=True
    )


class Subject(Base):
    __tablename__ = "subjects"
    id: Mapped[uuid.UUID] = _uuid_pk()
    key: Mapped[str] = mapped_column(String, nullable=False, unique=True)  # 'math' | 'language' | ...
    name: Mapped[str] = mapped_column(String, nullable=False)


class Skill(Base):
    __tablename__ = "skills"
    __table_args__ = (UniqueConstraint("subject_id", "key", name="uq_skills_subject_key"),)
    id: Mapped[uuid.UUID] = _uuid_pk()
    subject_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("subjects.id"))
    key: Mapped[str] = mapped_column(String, nullable=False)  # e.g. 'complete-the-square'
    name: Mapped[str] = mapped_column(String, nullable=False)
    grade_level: Mapped[int] = mapped_column(Integer, nullable=False)


class SkillEdge(Base):
    __tablename__ = "skill_edges"
    from_skill: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    )
    to_skill: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    )
    kind: Mapped[str] = mapped_column(
        String, primary_key=True, nullable=False, server_default=text("'prerequisite'")
    )  # prerequisite | related


class ContentNote(Base):
    __tablename__ = "content_notes"
    id: Mapped[uuid.UUID] = _uuid_pk()
    skill_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("skills.id"))
    source_path: Mapped[str] = mapped_column(String, nullable=False)
    prose: Mapped[str] = mapped_column(Text, nullable=False)  # prose WITHOUT code fences
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ContentEmbedding(Base):
    __tablename__ = "content_embeddings"
    id: Mapped[uuid.UUID] = _uuid_pk()
    note_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_notes.id", ondelete="CASCADE")
    )
    chunk: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)
    sidecar_query: Mapped[str | None] = mapped_column(Text)  # split-out ```sql block


class Attempt(Base):
    __tablename__ = "attempts"
    id: Mapped[uuid.UUID] = _uuid_pk()
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("skills.id"), nullable=False)
    item_ref: Mapped[str] = mapped_column(String, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    raw_answer: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class LearnerState(Base):
    __tablename__ = "learner_state"
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("skills.id"), primary_key=True)
    mastery: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, server_default=text("0.0")
    )  # P(known)
    uncertainty: Mapped[float] = mapped_column(
        Float, nullable=False, default=1.0, server_default=text("1.0")
    )  # Open Learner Model (P5)
    attempts_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TeacherNote(Base):
    __tablename__ = "teacher_notes"
    id: Mapped[uuid.UUID] = _uuid_pk()
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("teachers.id"), nullable=False)
    skill_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("skills.id"))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    override_mastery: Mapped[float | None] = mapped_column(Float)  # teacher override (P6)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
