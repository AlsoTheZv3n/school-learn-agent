"""Student endpoints (API-1, safety-critical). Every access runs in a scoped_session.

POST /student/turn drives the agent loop; GET /student/mastery returns the gentle
view (mastery %, no uncertainty — P5 enforced here, not just in the UI).
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text

from its.agent.graph import run_turn
from its.agent.state import TutorState
from its.api.schemas import GradeOut, StudentSkillMastery, TurnRequest, TurnResponse
from its.auth.deps import Principal, current_principal
from its.content.items import public_items
from its.db.session import scoped_session
from its.retrieval.individual import mastery_overview

router = APIRouter(prefix="/student", tags=["student"])


@router.post("/turn", response_model=TurnResponse)
def turn(req: TurnRequest, principal: Principal = Depends(current_principal)) -> TurnResponse:
    state = TutorState(
        student_id=principal.student_id or "",
        subject_key=req.subject_key,
        skill_key=req.skill_key,
        intent=req.intent,
        answer=req.answer,
        item_ref=req.item_ref,
    )
    with scoped_session(principal) as session:  # sets role + student_id context (RLS)
        result = run_turn(state, session=session)
    return TurnResponse(
        grade=GradeOut(**result.grade) if result.grade else None,
        mastery=result.mastery,
        explanation=result.explanation,
        route_reason=result.route_reason,
    )


@router.get("/mastery", response_model=list[StudentSkillMastery])
def my_mastery(principal: Principal = Depends(current_principal)) -> list[StudentSkillMastery]:
    with scoped_session(principal) as session:
        rows = mastery_overview(session, principal)
    # Drop uncertainty before it leaves the API (gentle view, P5).
    return [
        StudentSkillMastery(
            skill_id=r["skill_id"],
            name=r["name"],
            mastery=r["mastery"],
            attempts_count=r["attempts_count"],
        )
        for r in rows
    ]


_OVERVIEW_SQL = text(
    """
    SELECT sub.key AS subject_key, sub.name AS subject_name,
           sk.key AS skill_key, sk.name AS skill_name,
           ls.mastery, ls.attempts_count
    FROM learner_state ls
    JOIN skills sk ON sk.id = ls.skill_id
    JOIN subjects sub ON sub.id = sk.subject_id
    ORDER BY sub.name, sk.name
    """
)


@router.get("/overview")
def overview(principal: Principal = Depends(current_principal)) -> dict:
    """Composed home payload: subject progress, the concept to continue, recommendations,
    and the latest teacher note (gentle — no uncertainty, P5)."""
    with scoped_session(principal) as session:
        rows = [dict(r) for r in session.execute(_OVERVIEW_SQL).mappings().all()]
        note = (
            session.execute(
                text(
                    "SELECT body, created_at FROM teacher_notes "
                    "ORDER BY created_at DESC LIMIT 1"
                )
            )
            .mappings()
            .first()
        )

    # subjects: average mastery per subject
    subjects: dict[str, dict] = {}
    for r in rows:
        s = subjects.setdefault(
            r["subject_key"], {"key": r["subject_key"], "name": r["subject_name"], "_sum": 0.0, "_n": 0}
        )
        s["_sum"] += float(r["mastery"])
        s["_n"] += 1
    subject_list = [
        {"key": s["key"], "name": s["name"], "mastery": round(s["_sum"] / s["_n"], 3) if s["_n"] else 0.0}
        for s in subjects.values()
    ]

    practiced = [r for r in rows if r["attempts_count"] > 0]
    # "current": the practiced skill with the lowest mastery (most in need); fallback first skill
    current = None
    pool = practiced or rows
    if pool:
        c = min(pool, key=lambda r: r["mastery"])
        item = next(iter(public_items(c["skill_key"])), None)
        current = {
            "subject_key": c["subject_key"],
            "subject_name": c["subject_name"],
            "skill_key": c["skill_key"],
            "skill_name": c["skill_name"],
            "mastery": round(float(c["mastery"]), 3),
            "item_ref": item["item_ref"] if item else None,
            "prompt": item["prompt"] if item else None,
        }
    # recommendations: lowest-mastery skills not already "current"
    recs = sorted(rows, key=lambda r: r["mastery"])[:3]
    recommendations = [
        {"skill_key": r["skill_key"], "name": r["skill_name"], "subject_name": r["subject_name"]}
        for r in recs
        if not current or r["skill_key"] != current["skill_key"]
    ][:2]

    return {
        "subjects": subject_list,
        "current": current,
        "recommendations": recommendations,
        "note": ({"body": note["body"]} if note else None),
        "goal": {"practiced": len(practiced), "total": len(rows)},
    }


@router.get("/notes")
def my_notes(principal: Principal = Depends(current_principal)) -> list[dict]:
    """Teacher notes about me (the human in the loop is visible to the student, P6)."""
    with scoped_session(principal) as session:
        rows = (
            session.execute(
                text(
                    "SELECT tn.body, sk.name AS skill_name, tn.created_at "
                    "FROM teacher_notes tn LEFT JOIN skills sk ON sk.id = tn.skill_id "
                    "ORDER BY tn.created_at DESC"
                )
            )
            .mappings()
            .all()
        )
    return [
        {"body": r["body"], "skill_name": r["skill_name"], "created_at": str(r["created_at"])}
        for r in rows
    ]
