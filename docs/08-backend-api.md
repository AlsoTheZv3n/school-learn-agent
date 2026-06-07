# 08 — Backend-API (E9, M4)

**Ziel:** HTTP-Endpoints für Schüler- und Lehrer-Seite. Jeder personenbezogene Zugriff läuft
durch Scoping (SAF-2) und RLS; Aggregate durch Min-Cohort (SAF-3).

**Voraussetzungen:** AG-1 (Agent), SAF-2/3, RET-4, API der Modelle.
**Issues:** API-1 … API-3.

---

## 1. Schemas + Fehlermodell (API-3)

`apps/api/src/its/api/schemas.py`:

```python
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

class SkillMastery(BaseModel):
    skill_id: str
    name: str
    mastery: float
    uncertainty: float          # Open Learner Model (P5) — Lehrerseite zeigt das
    attempts_count: int

class CohortStat(BaseModel):
    n: int
    avg_mastery: float
```

Einheitliches Fehlermodell: `ScopeError`/`CohortTooSmall` → `403`; `LookupError` → `404`;
Validierung → `422` (FastAPI default). Ein Exception-Handler mappt die Safety-Exceptions auf
`403` mit neutraler Meldung (keine Detail-Leaks).

---

## 2. Student-Endpoints (API-1) · `safety-critical`

`apps/api/src/its/api/student.py`:

```python
from fastapi import APIRouter, Depends
from its.auth.deps import Principal, current_principal
from its.db.session import scoped_session
from its.agent.graph import build_graph
from its.agent.state import TutorState
from its.api.schemas import TurnRequest, TurnResponse

router = APIRouter(prefix="/student", tags=["student"])
_graph = build_graph()

@router.post("/turn", response_model=TurnResponse)
def turn(req: TurnRequest, principal: Principal = Depends(current_principal)) -> TurnResponse:
    # Schüler-Principal -> Scope ist die eigene student_id (fail-closed in scoped_session)
    state = TutorState(student_id=principal.student_id or "", subject_key=req.subject_key,
                       skill_key=req.skill_key, intent=req.intent,
                       answer=req.answer, item_ref=req.item_ref)
    with scoped_session(principal):     # setzt Rolle + student_id-Kontext (RLS)
        result: TutorState = _graph.invoke(state)
    return TurnResponse(grade=result.grade and GradeOut(**result.grade),
                        mastery=result.mastery, explanation=result.explanation,
                        route_reason=result.route_reason)

@router.get("/mastery", response_model=list[SkillMastery])
def my_mastery(principal: Principal = Depends(current_principal)) -> list[SkillMastery]:
    from its.retrieval.individual import mastery_overview
    with scoped_session(principal) as s:
        rows = mastery_overview(s, principal)
    return [SkillMastery(**r) for r in rows]
```

> Der Schüler-Mastery-Endpoint liefert die schonende Sicht; die UI zeigt nur `mastery`
> (Prozent), nicht `uncertainty`. Die Rohschätzung inkl. Unsicherheit ist der Lehrerseite
> vorbehalten (P5).

---

## 3. Teacher-Endpoints (API-2) · `safety-critical`

`apps/api/src/its/api/teacher.py`:

```python
from fastapi import APIRouter, Depends
from its.auth.deps import Principal, current_principal
from its.db.session import scoped_session
from its.api.schemas import SkillMastery, CohortStat

router = APIRouter(prefix="/teacher", tags=["teacher"])

@router.get("/student/{student_id}/mastery", response_model=list[SkillMastery])
def student_mastery(student_id: str, principal: Principal = Depends(current_principal)):
    # RLS (teacher_*_in_class) stellt sicher: nur Schüler:innen der eigenen Klassen sichtbar.
    with scoped_session(principal) as s:
        rows = s.execute(text("""
          SELECT ls.skill_id::text, sk.name, ls.mastery, ls.uncertainty, ls.attempts_count
          FROM learner_state ls JOIN skills sk ON sk.id = ls.skill_id
          WHERE ls.student_id = :sid
        """).bindparams(sid=student_id)).mappings().all()
    return [SkillMastery(**r) for r in rows]   # inkl. uncertainty (Open Learner Model)

@router.get("/class/{class_id}/skill/{skill_id}/distribution", response_model=CohortStat)
def class_distribution(class_id: str, skill_id: str,
                       principal: Principal = Depends(current_principal)):
    from its.retrieval.population import skill_mastery_distribution
    with scoped_session(principal) as s:
        res = skill_mastery_distribution(s, class_id, skill_id)   # via enforce_min_cohort
    return CohortStat(n=res.n, avg_mastery=res.payload["avg_mastery"])

@router.post("/student/{student_id}/note")
def add_note(student_id: str, body: str, skill_id: str | None = None,
             override_mastery: float | None = None,
             principal: Principal = Depends(current_principal)):
    # Lehrer-Intervention (P6): Notiz + optionaler Mastery-Override.
    with scoped_session(principal) as s:
        s.execute(text("""
          INSERT INTO teacher_notes (student_id, teacher_id, skill_id, body, override_mastery)
          VALUES (:sid, :tid, :skid, :b, :ov)
        """).bindparams(sid=student_id, tid=principal.user_id, skid=skill_id,
                        b=body, ov=override_mastery))
    return {"status": "ok"}
```

**AK:** Lehrer sehen nur Schüler:innen ihrer Klassen (durch RLS erzwungen, nicht durch
Query-Disziplin); Kohorten-Endpoint verweigert kleine Gruppen; Notiz/Override schreibbar.

---

## 4. Router-Mount

In `main.py` die Router einhängen:

```python
from its.api.student import router as student_router
from its.api.teacher import router as teacher_router
app.include_router(student_router)
app.include_router(teacher_router)
```

---

## 5. Akzeptanzkriterien (gesamt)

- [ ] `POST /student/turn` fährt den Agent-Loop in einer `scoped_session` (API-1)
- [ ] `GET /student/mastery` liefert schonende Sicht (ohne Unsicherheit nach aussen) (API-1)
- [ ] `GET /teacher/student/{id}/mastery` inkl. Unsicherheit, RLS-gefiltert (API-2)
- [ ] `GET /teacher/class/{id}/skill/{id}/distribution` via Min-Cohort (API-2)
- [ ] `POST /teacher/student/{id}/note` schreibt Notiz/Override (API-2)
- [ ] Safety-Exceptions → `403` neutral; Schemas vollständig (API-3)

---

## Claude-Code-Prompt

```
Setze E9 (docs/08-backend-api.md) um: api/schemas.py (Pydantic), api/student.py (POST /student/turn
über den LangGraph in scoped_session; GET /student/mastery schonende Sicht) und api/teacher.py
(GET student/{id}/mastery inkl. uncertainty, GET class/{id}/skill/{id}/distribution via
enforce_min_cohort, POST student/{id}/note mit override). Registriere einen Exception-Handler:
ScopeError/CohortTooSmall->403 neutral, LookupError->404. Mounte die Router in main.py. Schreibe
HTTP-Tests gegen die Test-DB (Schüler sieht nur sich; Lehrer nur eigene Klasse; kleine Kohorte->403).
Schliesse API-1..3.
```
