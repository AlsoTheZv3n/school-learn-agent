"""History grader (GR-3): open response — tentative, with a teacher-override path (P6).

An LLM may later propose a rubric-based assessment, but confidence stays < 1.0 and a
teacher confirms. Here we use a transparent keyword-overlap heuristic against the
rubric/answer_key and report low confidence, so the agent's update_model does NOT
cement the result automatically (it only commits at confidence >= 0.9).
"""

import re

from its.grading.base import GradeResult, Item

_TOKEN = re.compile(r"\w+", re.UNICODE)
_CONFIDENCE = 0.5  # < 0.9 -> never auto-cemented; routed to teacher review


def _keywords(text: str) -> set[str]:
    return {t for t in _TOKEN.findall(text.casefold()) if len(t) > 3}


class HistoryGrader:
    subject_key = "history"

    def grade(self, answer: str, item: Item) -> GradeResult:
        reference = _keywords(f"{item.answer_key} {item.rubric or ''}")
        if not reference:
            return GradeResult(False, "Kein Bewertungsmassstab hinterlegt.", _CONFIDENCE)
        got = _keywords(answer)
        overlap = len(got & reference) / len(reference)
        tentative_correct = overlap >= 0.5
        return GradeResult(
            tentative_correct,
            "Vorläufige Einschätzung — wird von einer Lehrperson überprüft.",
            _CONFIDENCE,
        )
