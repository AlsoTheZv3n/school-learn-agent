"""Language grader (GR-3): rule-based, deterministic where possible.

The curated answer_key may list accepted forms separated by '|'. Comparison is
case-insensitive and whitespace-normalized. Deterministic -> confidence 1.0.
"""

import re

from its.grading.base import GradeResult, Item

_WS = re.compile(r"\s+")


def _norm(s: str) -> str:
    return _WS.sub(" ", s).strip().casefold()


class LanguageGrader:
    subject_key = "language"

    def grade(self, answer: str, item: Item) -> GradeResult:
        accepted = {_norm(a) for a in item.answer_key.split("|")}
        correct = _norm(answer) in accepted
        return GradeResult(
            correct,
            "Richtig." if correct else "Noch nicht — achte auf die erwartete Form.",
            1.0,
        )
