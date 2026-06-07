"""Request/response schemas (API-3). Validation feeds safe query templates.

Two mastery views over the same learner_state row (P5 enforced at the API boundary,
not just the UI): the student view omits `uncertainty`; the teacher view includes it.
"""

from pydantic import BaseModel

from its.agent.state import Intent


class TurnRequest(BaseModel):
    subject_key: str
    skill_key: str
    intent: Intent
    answer: str | None = None
    item_ref: str | None = None


class GradeOut(BaseModel):
    correct: bool
    feedback: str
    confidence: float


class TurnResponse(BaseModel):
    grade: GradeOut | None = None
    mastery: float | None = None
    explanation: str | None = None
    route_reason: str | None = None


class StudentSkillMastery(BaseModel):
    """Gentle student view — deliberately WITHOUT uncertainty (P5)."""

    skill_id: str
    name: str
    mastery: float
    attempts_count: int


class SkillMastery(BaseModel):
    """Teacher view — includes uncertainty (open learner model, P5)."""

    skill_id: str
    name: str
    mastery: float
    uncertainty: float
    attempts_count: int


class CohortStat(BaseModel):
    n: int
    avg_mastery: float


class NoteRequest(BaseModel):
    body: str
    skill_id: str | None = None
    override_mastery: float | None = None
