"""retrieve node (AG-2): fetch material/state via the appropriate mode (RLS/cohort aware).

Best-effort: retrieval never breaks a turn (failures yield an empty context). For an
answer/next turn with scope we pull the student's mastery (individual, scoped + RLS);
otherwise we pull shared explanatory chunks (semantic).
"""

from collections.abc import Callable

from sqlalchemy.orm import Session

from its.agent.state import Intent, TutorState
from its.auth.deps import Principal
from its.auth.roles import Role
from its.llm.embeddings import Embedder
from its.retrieval.individual import mastery_overview
from its.retrieval.semantic import semantic_search_text


def make_retrieve_node(session: Session, embedder: Embedder | None = None) -> Callable:
    def retrieve_node(state: TutorState) -> dict:
        try:
            if state.intent in (Intent.ANSWER, Intent.NEXT) and state.student_id:
                principal = Principal(
                    user_id=state.student_id, role=Role.STUDENT, student_id=state.student_id
                )
                retrieved = mastery_overview(session, principal)
            else:
                retrieved = semantic_search_text(session, state.skill_key, k=3, embedder=embedder)
        except Exception:
            retrieved = []
        return {"retrieved": retrieved}

    return retrieve_node
