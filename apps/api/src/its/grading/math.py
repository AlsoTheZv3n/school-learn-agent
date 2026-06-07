"""Math grader (GR-2): symbolic/numeric check against the CURATED answer key.

No LLM generation of the key (P2). Equivalent algebraic forms are accepted
(x^2+2x+1 == (x+1)^2) because the check is symbolic. confidence is always 1.0:
the result is deterministic.
"""

import sympy as sp

from its.grading.base import GradeResult, Item

# Allow caret as exponent (student-friendly) -> sympy's **.
_TRANSFORMS = sp.parsing.sympy_parser.standard_transformations + (
    sp.parsing.sympy_parser.convert_xor,
)


class MathGrader:
    subject_key = "math"

    def _parse(self, expr: str) -> sp.Expr:
        return sp.parsing.sympy_parser.parse_expr(expr, transformations=_TRANSFORMS, evaluate=True)

    def grade(self, answer: str, item: Item) -> GradeResult:
        try:
            got = self._parse(answer)
            expected = self._parse(item.answer_key)
            correct = bool(sp.simplify(got - expected) == 0)
        except Exception:  # noqa: BLE001 — any parse/eval failure -> not a readable term
            return GradeResult(False, "Konnte die Eingabe nicht als Term lesen.", 1.0)
        return GradeResult(
            correct,
            "Richtig." if correct else "Noch nicht — prüfe deine Umformung.",
            1.0,
        )
