"""Retrieval router (RET-1): decide scope + whether to escalate to a live query.

Deliberately rule-based to start (auditable via RouteDecision.reason); replace with
a small classifier only if needed — the explicit reason field stays. The decision
is logged (P6: auditable routing).
"""

import logging
from dataclasses import dataclass
from enum import StrEnum

log = logging.getLogger(__name__)


class Mode(StrEnum):
    SEMANTIC = "semantic"
    INDIVIDUAL = "individual"
    POPULATION = "population"


@dataclass(frozen=True)
class RouteDecision:
    mode: Mode
    escalate_to_query: bool  # True = structured live query, not just prose
    reason: str


# Aggregate / comparison cues -> population.
_POPULATION = (
    "klasse", "alle", "durchschnitt", "verteilung", "kohorte", "wie viele",
    "class", "everyone", "average", "distribution", "cohort", "how many",
)
# Personal-progress cues (only meaningful with a student scope) -> individual.
_INDIVIDUAL = (
    "mein", "meine", "wo stehe ich", "mein stand", "mein fortschritt",
    "my progress", "where do i stand", "my mastery", "how am i doing",
)
# Cues that a fresh/precise number is wanted -> escalate to a live query.
_ESCALATE = ("genau", "aktuell", "zahl", "prozent", "exact", "current", "number", "percent")


def route(question: str, *, has_student_scope: bool) -> RouteDecision:
    q = question.lower()
    if any(w in q for w in _POPULATION):
        mode, reason = Mode.POPULATION, "aggregate/comparison cue"
    elif has_student_scope and any(w in q for w in _INDIVIDUAL):
        mode, reason = Mode.INDIVIDUAL, "personal-progress cue with student scope"
    else:
        mode, reason = Mode.SEMANTIC, "explanatory default"
    escalate = any(w in q for w in _ESCALATE)
    decision = RouteDecision(mode=mode, escalate_to_query=escalate, reason=reason)
    log.info("route q=%r -> mode=%s escalate=%s (%s)", question, mode.value, escalate, reason)
    return decision
