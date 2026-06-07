"""DEV-ONLY helpers (mounted only when AUTH_DEV_MODE=1). Never enable in production.

Exposes a sample identity from the seeded mock data so the frontend can log in as a
real seeded student / teacher without a real IdP.
"""

from fastapi import APIRouter
from sqlalchemy import text

from its.db.session import SessionLocal

router = APIRouter(prefix="/dev", tags=["dev"])


@router.get("/seed-info")
def seed_info() -> dict:
    """Return one (class, teacher, student) triple from the seeded data (owner read)."""
    with SessionLocal() as session:
        row = (
            session.execute(
                text(
                    """
                    SELECT c.id::text AS class_id, c.teacher_id::text AS teacher_id,
                           e.student_id::text AS student_id, st.display_name AS student_name
                    FROM classes c
                    JOIN enrollments e ON e.class_id = c.id
                    JOIN students st ON st.id = e.student_id
                    WHERE c.teacher_id IS NOT NULL
                    ORDER BY st.display_name
                    LIMIT 1
                    """
                )
            )
            .mappings()
            .first()
        )
    return dict(row) if row else {}
