"""explain node (AG-2): the generative, error-tolerant path (P2).

Receives only anonymized context (skill_key, intent) — never a name (P4). The LLM
client also scrubs defensively. Mistakes here are minor and visible (the child just
asks again), unlike the assess path which must be trustworthy.
"""

from collections.abc import Callable

from its.agent.state import TutorState
from its.llm.client import complete as default_complete
from its.llm.prompts import EXPLAIN_SYSTEM


def make_explain_node(complete_fn: Callable[..., str] | None = None) -> Callable:
    complete = complete_fn or default_complete

    def explain_node(state: TutorState) -> dict:
        # anonymized context only: skill key + intent, no PII.
        prompt = (
            f"Skill: {state.skill_key}. Modus: {state.intent.value}. "
            "Formuliere eine kurze, andere Erklärung oder einen Hinweis."
        )
        return {"explanation": complete(system=EXPLAIN_SYSTEM, user=prompt)}

    return explain_node
