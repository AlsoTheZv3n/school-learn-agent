"""Teacher endpoints (API-2, safety-critical).

RLS (teacher_*_in_class) ensures a teacher sees only students in their own classes —
the UI/queries need no extra filtering. Aggregates go through the min-cohort gate.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text

from its.api.schemas import CohortStat, NoteRequest, SkillMastery
from its.auth.deps import Principal, current_principal
from its.db.session import scoped_session
from its.retrieval.population import skill_mastery_distribution

router = APIRouter(prefix="/teacher", tags=["teacher"])


@router.get("/student/{student_id}/mastery", response_model=list[SkillMastery])
def student_mastery(
    student_id: str, principal: Principal = Depends(current_principal)
) -> list[SkillMastery]:
    with scoped_session(principal) as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT ls.skill_id::text AS skill_id, sk.name, ls.mastery,
                           ls.uncertainty, ls.attempts_count
                    FROM learner_state ls JOIN skills sk ON sk.id = ls.skill_id
                    WHERE ls.student_id = :sid
                    """
                ),
                {"sid": student_id},
            )
            .mappings()
            .all()
        )
    return [SkillMastery(**r) for r in rows]  # incl. uncertainty (open learner model)


@router.get(
    "/class/{class_id}/skill/{skill_id}/distribution", response_model=CohortStat
)
def class_distribution(
    class_id: str, skill_id: str, principal: Principal = Depends(current_principal)
) -> CohortStat:
    with scoped_session(principal) as session:
        res = skill_mastery_distribution(session, class_id, skill_id)  # via enforce_min_cohort
    return CohortStat(n=res.n, avg_mastery=res.payload["avg_mastery"])


@router.post("/student/{student_id}/note")
def add_note(
    student_id: str, note: NoteRequest, principal: Principal = Depends(current_principal)
) -> dict:
    with scoped_session(principal) as session:
        session.execute(
            text(
                """
                INSERT INTO teacher_notes (student_id, teacher_id, skill_id, body, override_mastery)
                VALUES (:sid, :tid, :skid, :body, :ov)
                """
            ),
            {
                "sid": student_id,
                "tid": principal.user_id,
                "skid": note.skill_id,
                "body": note.body,
                "ov": note.override_mastery,
            },
        )
    return {"status": "ok"}
