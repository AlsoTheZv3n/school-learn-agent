"""Production data import (E14). Separate from mock; requires DATA_MODE=prod.

- Roster: validated rows (Pydantic) upserted by stable external IDs (idempotent).
- Content: goes through the regular ingestion pipeline (CON-2) — no special path.
Never mix mock and real data in the same database.
"""

import argparse
import csv
import os
import sys

from pydantic import BaseModel, ValidationError, field_validator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from its.content.ingest import ingest_vault


def require_prod() -> None:
    if os.environ.get("DATA_MODE") != "prod":
        sys.exit("REFUSED: import_production requires DATA_MODE=prod.")


class RosterRow(BaseModel):
    external_id: str
    display_name: str
    grade_level: int
    class_external_id: str
    class_name: str

    @field_validator("grade_level")
    @classmethod
    def _grade_in_range(cls, v: int) -> int:
        if not 1 <= v <= 13:
            raise ValueError("grade_level out of range (1..13)")
        return v


def import_roster(session: Session, path: str) -> int:
    """Upsert classes/students/enrollments from a validated CSV. Idempotent."""
    with open(path, newline="", encoding="utf-8") as f:
        rows = [RosterRow(**raw) for raw in csv.DictReader(f)]
    for r in rows:
        class_id = session.execute(
            text(
                "INSERT INTO classes (name, external_id) VALUES (:n, :ext) "
                "ON CONFLICT (external_id) DO UPDATE SET name = EXCLUDED.name RETURNING id"
            ),
            {"n": r.class_name, "ext": r.class_external_id},
        ).scalar()
        student_id = session.execute(
            text(
                "INSERT INTO students (display_name, grade_level, external_id) "
                "VALUES (:n, :g, :ext) ON CONFLICT (external_id) DO UPDATE SET "
                "display_name = EXCLUDED.display_name, grade_level = EXCLUDED.grade_level RETURNING id"
            ),
            {"n": r.display_name, "g": r.grade_level, "ext": r.external_id},
        ).scalar()
        session.execute(
            text(
                "INSERT INTO enrollments (student_id, class_id) VALUES (:s, :c) "
                "ON CONFLICT DO NOTHING"
            ),
            {"s": student_id, "c": class_id},
        )
    return len(rows)


def import_content(session: Session, vault_dir: str) -> int:
    """Real learning material through the same ingestion pipeline as mock (CON-2)."""
    return ingest_vault(session, vault_dir)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="ITS production import (DATA_MODE=prod only).")
    ap.add_argument("--roster", help="CSV path: external_id,display_name,grade_level,class_external_id,class_name")
    ap.add_argument("--content", help="vault directory of curated markdown")
    args = ap.parse_args(argv)

    require_prod()
    engine = create_engine(os.environ["DATABASE_URL"])
    session_factory = sessionmaker(bind=engine)
    with session_factory() as session:
        try:
            if args.roster:
                n = import_roster(session, args.roster)
                print(f"roster imported/updated: {n} rows")
            if args.content:
                n = import_content(session, args.content)
                print(f"content notes ingested: {n}")
        except ValidationError as e:
            session.rollback()
            sys.exit(f"REFUSED: invalid roster data:\n{e}")
        session.commit()


if __name__ == "__main__":
    main()
