"""Grading: the one real plugin seam (P7), keyed on subject.

Graders register themselves on import. Everything else in the system (tracing loop,
router, dashboard) stays a single implementation — only grading is pluginized.
"""

from its.grading.history import HistoryGrader
from its.grading.language import LanguageGrader
from its.grading.math import MathGrader
from its.grading.registry import get_grader, register, registered_subjects

register(MathGrader())
register(LanguageGrader())
register(HistoryGrader())

__all__ = ["get_grader", "register", "registered_subjects"]
