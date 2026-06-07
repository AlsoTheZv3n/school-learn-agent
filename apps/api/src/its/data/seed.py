"""Mock-data seeder (E13). Realistic, non-uniform learning curves.

Mastery is derived through the SAME tracing service as live (record_attempt), so the
demo's open learner model is consistent with production behavior (P3). Refuses to run
unless DATA_MODE=mock (guard), and so does --reset.
"""

import argparse
import os
import random
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from its.db.models import Attempt, Class, Enrollment, Student
from its.learner_model.tracing import record_attempt

_DEMO_STUDENTS = 25


def guard_mock() -> None:
    if os.environ.get("DATA_MODE", "mock") != "mock":
        sys.exit("REFUSED: seeding is disabled when DATA_MODE != 'mock' (see docs/11).")


def ensure_curriculum(session: Session) -> list[dict]:
    """Ensure the math subject + skills exist (idempotent). Returns the skills."""
    session.execute(
        text("INSERT INTO subjects (key, name) VALUES ('math', 'Mathematik') ON CONFLICT (key) DO NOTHING")
    )
    rows = (
        session.execute(
            text(
                "SELECT s.id, s.key FROM skills s JOIN subjects sub ON sub.id = s.subject_id "
                "WHERE sub.key = 'math' ORDER BY s.grade_level, s.key"
            )
        )
        .mappings()
        .all()
    )
    return [dict(r) for r in rows]


def simulate_history(session: Session, student_id, skills: list[dict], rng: random.Random) -> None:
    """Non-uniform curve: a latent ability per student; P(correct) rises with practice."""
    ability = rng.betavariate(2, 2)
    for skill in skills:
        n = rng.randint(4, 12)
        for i in range(n):
            p_correct = min(0.95, ability * (0.5 + 0.05 * i))
            correct = rng.random() < p_correct
            session.add(
                Attempt(
                    student_id=student_id,
                    skill_id=skill["id"],
                    item_ref=f"seed-{skill['key']}-{i}",
                    is_correct=correct,
                )
            )
            record_attempt(session, student_id, skill["id"], correct)  # same logic as live


def seed(
    session: Session,
    *,
    profile: str = "demo",
    classes: int = 3,
    students_per_class: int = 20,
    rng: random.Random | None = None,
) -> dict:
    """Seed classes/students/attempts + derived learner_state. Returns created ids."""
    rng = rng or random.Random()
    skills = ensure_curriculum(session)
    created: dict[str, list] = {"classes": [], "students": []}
    if profile == "empty":
        return created
    n_classes = 1 if profile == "demo" else classes
    n_students = _DEMO_STUDENTS if profile == "demo" else students_per_class
    for ci in range(n_classes):
        klass = Class(name=f"Demo-Klasse {ci + 1}")
        session.add(klass)
        session.flush()
        created["classes"].append(klass.id)
        for si in range(n_students):
            student = Student(display_name=f"Schüler:in {ci + 1}-{si + 1}", grade_level=9)
            session.add(student)
            session.flush()
            session.add(Enrollment(student_id=student.id, class_id=klass.id))
            simulate_history(session, student.id, skills, rng)
            created["students"].append(student.id)
    return created


def reset(session: Session) -> None:
    """Empty the person-scoped tables (dev only — caller must guard)."""
    session.execute(
        text(
            "TRUNCATE teacher_notes, attempts, learner_state, enrollments, classes, students "
            "RESTART IDENTITY CASCADE"
        )
    )


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="ITS mock-data seeder (DATA_MODE=mock only).")
    ap.add_argument("--profile", choices=["demo", "load", "empty"], default="demo")
    ap.add_argument("--classes", type=int, default=3)
    ap.add_argument("--students-per-class", type=int, default=20)
    ap.add_argument("--seed", type=int, default=None, help="rng seed for reproducible demos")
    ap.add_argument("--reset", action="store_true")
    args = ap.parse_args(argv)

    guard_mock()  # both seeding and reset are mock-only
    engine = create_engine(os.environ["DATABASE_URL"])
    session_factory = sessionmaker(bind=engine)
    with session_factory() as session:
        if args.reset:
            reset(session)
            print("reset: person tables truncated")
        else:
            rng = random.Random(args.seed) if args.seed is not None else random.Random()
            created = seed(
                session,
                profile=args.profile,
                classes=args.classes,
                students_per_class=args.students_per_class,
                rng=rng,
            )
            print(f"seeded: {len(created['classes'])} classes, {len(created['students'])} students")
        session.commit()


if __name__ == "__main__":
    main()
