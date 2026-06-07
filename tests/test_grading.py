"""Grading tests (GR-1..3): math (curated key), language, history, registry."""

import pytest

from its.grading import get_grader
from its.grading.base import Item
from its.grading.history import HistoryGrader
from its.grading.language import LanguageGrader
from its.grading.math import MathGrader


def test_math_equivalent_forms_accepted() -> None:
    g = MathGrader()
    item = Item(skill_key="expand", prompt="(x+1)^2", answer_key="x**2 + 2*x + 1")
    assert g.grade("x^2+2*x+1", item).correct is True  # caret + equivalent form


def test_math_wrong_rejected_with_full_confidence() -> None:
    g = MathGrader()
    item = Item(skill_key="expand", prompt="(x+1)^2", answer_key="x**2 + 2*x + 1")
    r = g.grade("x^2+1", item)
    assert r.correct is False
    assert r.confidence == 1.0


def test_math_unparseable_is_not_correct() -> None:
    g = MathGrader()
    item = Item(skill_key="x", prompt="", answer_key="x+1")
    assert g.grade("@@@ not math @@@", item).correct is False


def test_registry_keys_on_subject() -> None:
    assert get_grader("math").subject_key == "math"
    assert get_grader("language").subject_key == "language"
    assert get_grader("history").subject_key == "history"


def test_registry_unknown_subject_raises() -> None:
    with pytest.raises(LookupError):
        get_grader("chemistry")


def test_language_accepts_listed_forms() -> None:
    g = LanguageGrader()
    item = Item(
        skill_key="greet", prompt="Hallo auf Englisch", answer_key="hello|hi",
        subject_key="language",
    )
    assert g.grade("Hello", item).correct is True
    assert g.grade("bonjour", item).correct is False


def test_history_is_low_confidence_for_teacher_review() -> None:
    g = HistoryGrader()
    item = Item(
        skill_key="ww1", prompt="Ursachen?", answer_key="Attentat Sarajevo Bündnis",
        rubric="Nenne Ursachen", subject_key="history",
    )
    r = g.grade("Das Attentat von Sarajevo und die Bündnissysteme.", item)
    assert r.confidence < 0.9  # never auto-cemented; routed to teacher (P6)
