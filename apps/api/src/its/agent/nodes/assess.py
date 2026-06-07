"""assess node (AG-2): curated grading (P2).

Loads the CURATED item (answer_key is not LLM-generated) and grades the answer with
the subject's registered grader. Importing the registry triggers grader registration.
"""

from its.agent.state import TutorState
from its.content.items import load_item
from its.grading.registry import get_grader  # importing the package registers graders


def assess_node(state: TutorState) -> dict:
    if state.answer is None or state.item_ref is None:
        return {}
    item = load_item(state.item_ref)  # curated, NOT from an LLM
    grader = get_grader(state.subject_key)
    result = grader.grade(state.answer, item)
    return {
        "grade": {
            "correct": result.correct,
            "feedback": result.feedback,
            "confidence": result.confidence,
        }
    }
