"""Shared content endpoints: curated items (without keys) + the curriculum graph.

This is study material, not person-scoped data — no RLS needed. Crucially, the
answer_key is NEVER exposed (P2): students receive only the prompt.
"""

from fastapi import APIRouter
from sqlalchemy import text

from its.content.items import public_items
from its.db.session import SessionLocal

router = APIRouter(tags=["content"])


@router.get("/content/items")
def items(skill_key: str | None = None) -> list[dict]:
    return public_items(skill_key)


@router.get("/curriculum")
def curriculum() -> dict:
    with SessionLocal() as session:
        subjects = (
            session.execute(text("SELECT key, name FROM subjects ORDER BY name")).mappings().all()
        )
        skills = (
            session.execute(
                text(
                    "SELECT sk.id::text AS skill_id, sk.key, sk.name, sub.key AS subject_key, "
                    "sk.grade_level FROM skills sk JOIN subjects sub ON sub.id = sk.subject_id "
                    "ORDER BY sk.grade_level, sk.name"
                )
            )
            .mappings()
            .all()
        )
        edges = (
            session.execute(
                text(
                    "SELECT f.key AS from_key, t.key AS to_key, e.kind FROM skill_edges e "
                    "JOIN skills f ON f.id = e.from_skill JOIN skills t ON t.id = e.to_skill"
                )
            )
            .mappings()
            .all()
        )
    return {
        "subjects": [dict(x) for x in subjects],
        "skills": [dict(x) for x in skills],
        "edges": [dict(x) for x in edges],
        "items": public_items(),
    }
