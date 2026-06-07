"""Student endpoints (API-1, safety-critical). Every access runs in a scoped_session.

POST /student/turn drives the agent loop; GET /student/mastery returns the gentle
view (mastery %, no uncertainty — P5 enforced here, not just in the UI).
"""

from fastapi import APIRouter, Depends

from its.agent.graph import run_turn
from its.agent.state import TutorState
from its.api.schemas import GradeOut, StudentSkillMastery, TurnRequest, TurnResponse
from its.auth.deps import Principal, current_principal
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
