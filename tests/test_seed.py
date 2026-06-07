"""Tests for the mock seeder (E13) and production import (E14).

DB tests run in a transaction that is rolled back, so nothing persists and other
tests are unaffected.
"""

import random

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from its.data.production import import_roster, require_prod
from its.data.seed import guard_mock, seed


def test_guard_mock_refuses_when_not_mock(monkeypatch) -> None:
    monkeypatch.setenv("DATA_MODE", "prod")
    with pytest.raises(SystemExit):
        guard_mock()


def test_guard_mock_allows_mock(monkeypatch) -> None:
    monkeypatch.setenv("DATA_MODE", "mock")
    guard_mock()  # must not raise


def test_require_prod_refuses_when_not_prod(monkeypatch) -> None:
    monkeypatch.delenv("DATA_MODE", raising=False)
    with pytest.raises(SystemExit):
        require_prod()


def test_seed_creates_attempts_and_state(engine) -> None:
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        created = seed(session, profile="load", classes=1, students_per_class=3, rng=random.Random(42))
        assert len(created["students"]) == 3
        for sid in created["students"]:
            attempts = session.execute(
                text("SELECT count(*) FROM attempts WHERE student_id = :s"), {"s": sid}
            ).scalar()
            states = session.execute(
                text("SELECT count(*) FROM learner_state WHERE student_id = :s"), {"s": sid}
            ).scalar()
            assert attempts > 0
            assert states > 0
        # non-uniform: mastery should vary across the seeded students (not all identical)
        masteries = session.execute(
            text("SELECT DISTINCT round(mastery::numeric, 4) FROM learner_state")
        ).scalars().all()
        assert len(masteries) > 1
    finally:
        session.rollback()  # nothing persisted
        session.close()


def test_roster_import_is_idempotent(engine, tmp_path) -> None:
    csv_path = tmp_path / "roster.csv"
    csv_path.write_text(
        "external_id,display_name,grade_level,class_external_id,class_name\n"
        "ext-stud-1,Test Person,9,ext-class-1,Test Klasse\n",
        encoding="utf-8",
    )
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        n1 = import_roster(session, str(csv_path))
        session.flush()
        n2 = import_roster(session, str(csv_path))  # second run upserts, no duplicate
        session.flush()
        count = session.execute(
            text("SELECT count(*) FROM students WHERE external_id = 'ext-stud-1'")
        ).scalar()
        assert n1 == 1
        assert n2 == 1
        assert count == 1  # idempotent
    finally:
        session.rollback()
        session.close()
