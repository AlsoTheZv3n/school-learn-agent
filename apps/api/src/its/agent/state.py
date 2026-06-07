"""Agent state + intents (AG-1)."""

from dataclasses import dataclass, field
from enum import StrEnum


class Intent(StrEnum):
    ANSWER = "answer"  # student submits an answer -> assess
    EXPLAIN = "explain"  # "explain differently"
    HINT = "hint"  # "a hint"
    WHY = "why"  # "why am I learning this"
    NEXT = "next"  # request the next question


@dataclass
class TutorState:
    student_id: str
    subject_key: str
    skill_key: str
    intent: Intent
    answer: str | None = None
    item_ref: str | None = None
    # results, filled by nodes:
    retrieved: list[dict] = field(default_factory=list)
    grade: dict | None = None
    mastery: float | None = None
    explanation: str | None = None
    route_reason: str | None = None
