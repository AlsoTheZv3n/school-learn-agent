"""route node (AG-2): pick mode + escalation via retrieval.router; record the reason."""

from its.agent.state import Intent, TutorState
from its.retrieval.router import route


def route_node(state: TutorState) -> dict:
    has_scope = bool(state.student_id)
    if state.intent in (Intent.ANSWER, Intent.NEXT):
        decision = route("mein fortschritt", has_student_scope=has_scope)  # tends individual
    else:
        decision = route(state.skill_key, has_student_scope=has_scope)  # tends semantic
    return {"route_reason": f"{decision.mode.value}:{decision.reason}"}
