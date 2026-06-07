## Ziel

Die Schüler-HTTP-Endpoints: `POST /student/turn` fährt den pädagogischen Agent-Loop (LangGraph) innerhalb einer `scoped_session` und gibt Bewertung/Erklärung/Mastery zurück; `GET /student/mastery` liefert die **schonende** Lernstandssicht. Am Ende kann ein:e authentifizierte:r Schüler:in eine Antwort einreichen bzw. eine Erklärung anfordern und den eigenen Stand sehen — und ausschliesslich den eigenen.

## Kontext & Prinzipien

- **P1 (Safety zuerst, in der DB):** Jeder Zugriff läuft durch `scoped_session(principal)`, die PG-Rolle `its_student` setzt und `app.current_student_id` als Session-Variable hinterlegt. Die RLS-Policy `student_state_self` / `student_attempts_self` filtert dann zeilenweise — selbst eine fehlerhafte Query liefert keine Fremdzeilen. Fail-closed: ohne `student_id` → `PermissionError` in `scoped_session`.
- **P5 (Open Learner Model, schonende Aussensicht):** `GET /student/mastery` ist die schonende Sicht; die UI zeigt nur `mastery` (Prozent), **nicht** `uncertainty`. Die Rohschätzung inkl. Unsicherheit ist der Lehrerseite vorbehalten (API-2).
- **P2 (kuratierte Bewertung):** Der `assess`-Pfad im Graph nutzt den kuratierten Grader, nicht freie LLM-Generierung — die API ruft nur `_graph.invoke`, erzwingt damit aber genau diesen Pfad für `intent=answer`.
- **P7 (eine Plugin-Naht):** Die API ist *eine* Implementierung, kein Strategy-Punkt. Keine Geschäftslogik hier — nur State bauen, Graph aufrufen, Response mappen.

## Zu erstellende/ändernde Dateien

- `apps/api/src/its/api/student.py` (neu) — Router mit `/student/turn` und `/student/mastery`.
- `apps/api/src/its/main.py` (ändern) — `app.include_router(student_router)`.

## Schnittstellen & Signaturen

Referenz-Implementierung aus `docs/08-backend-api.md` §2:

```python
from fastapi import APIRouter, Depends
from its.auth.deps import Principal, current_principal
from its.db.session import scoped_session
from its.agent.graph import build_graph
from its.agent.state import TutorState
from its.api.schemas import TurnRequest, TurnResponse, GradeOut, SkillMastery

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

> Korrektur zum Doc-Auszug: der Import von `GradeOut` (und `SkillMastery`) ist im Doc-Snippet nicht aufgeführt, wird aber verwendet — oben ergänzt.

Genutzte Bausteine (Referenz, nicht hier zu implementieren):

```python
# its.agent.state (AG-1)
@dataclass
class TutorState:
    student_id: str; subject_key: str; skill_key: str; intent: Intent
    answer: str | None = None; item_ref: str | None = None
    retrieved: list[dict] = field(default_factory=list)
    grade: dict | None = None; mastery: float | None = None
    explanation: str | None = None; route_reason: str | None = None

# its.db.session (DB-3) — fail-closed bei fehlender student_id
@contextmanager
def scoped_session(principal: Principal) -> Iterator[Session]: ...

# its.retrieval.individual (RET-3) — Scope via require_student_scope + RLS
def mastery_overview(session: Session, principal: Principal) -> list[dict]:
    # liefert dicts mit: skill_id, name, mastery, uncertainty, attempts_count
    ...

# its.auth.deps (FND-5) — vorerst Stub
@dataclass(frozen=True)
class Principal:
    user_id: str; role: Role; student_id: str | None = None
```

## Umsetzungsschritte

- [ ] `student.py` anlegen: `APIRouter(prefix="/student", tags=["student"])`, Modul-globaler `_graph = build_graph()`.
- [ ] `POST /turn` implementieren: `TurnRequest` → `TutorState` (mit `principal.student_id or ""`).
- [ ] Den `_graph.invoke(state)`-Aufruf in `with scoped_session(principal):` kapseln.
- [ ] Rückgabe von `_graph.invoke` defensiv behandeln: LangGraph kann ein **dict** statt der Dataclass liefern. Vor Attribut-Zugriff prüfen und einheitlich auslesen.
  > Hinweis: zu entscheiden — ob `result` Dataclass oder dict ist (offene Frage des Epics); nicht raten, sondern an AG-1 abstimmen und entsprechend `result.grade` vs. `result["grade"]` verwenden.
- [ ] `TurnResponse` mappen: `grade=GradeOut(**result.grade) if result.grade else None`, plus `mastery`/`explanation`/`route_reason`.
- [ ] `GET /mastery` implementieren: `mastery_overview(s, principal)` in `scoped_session`, Ergebnis als `list[SkillMastery]`.
- [ ] Sicherstellen, dass `SkillMastery(**r)` passt — falls `mastery_overview` `skill_id` als UUID liefert, in der Query/im Mapping zu `str` casten (RET-3 nutzt `ls.skill_id` direkt; ggf. `::text`-Cast wie in API-2).
  > Hinweis: zu entscheiden — UUID-zu-str-Cast-Ort (Query vs. Schema-Validator).
- [ ] In `main.py`: `from its.api.student import router as student_router; app.include_router(student_router)`.
- [ ] Klären, wie die request-scoped Session in die Agent-Nodes gelangt (der `update_model`-Node öffnet in docs/07 ein eigenes `SessionLocal()` ohne Rollen-/`student_id`-Kontext → RLS-Lücke).
  > Hinweis: zu entscheiden — Session-Injektion in den Graph (offene Frage des Epics; betrifft P1). Nicht eigenmächtig ein ungescoptes `SessionLocal()` zementieren.

## Akzeptanzkriterien

- [ ] `POST /student/turn` fährt den Agent-Loop **innerhalb** einer `scoped_session` (kein Aufruf ausserhalb).
- [ ] `GET /student/mastery` liefert die schonende Sicht; die nach aussen relevante Grösse ist `mastery` (UI zeigt `uncertainty` nicht).
- [ ] Ein:e Schüler:in sieht über `/student/mastery` ausschliesslich eigene Skills (RLS-erzwungen, nicht durch Query-Disziplin).
- [ ] Fehlt `principal.student_id` bei einem Schüler-Principal, schlägt der Request fail-closed fehl (`PermissionError` aus `scoped_session`, gemappt durch das Fehlermodell aus API-3).
- [ ] Beide Endpoints sind über den in `main.py` gemounteten Router erreichbar.

## Tests / Verifikation

Voraussetzung: Docker-DB läuft (`docker compose -f infra/docker-compose.yml up -d`), Migrationen + `rls.sql` angewandt. Auth in Tests via `app.dependency_overrides[current_principal]`.

- [ ] `uv run uvicorn its.main:app` startet; `curl http://localhost:8000/health` → `{"status":"ok"}`.
- [ ] `tests/test_api_student.py` (FastAPI-`TestClient`, `db_factory`/`two_students` aus docs/10):
  - Schüler A überschreibt `current_principal` → `GET /student/mastery` listet nur As Skills; keine Zeile von B.
  - `POST /student/turn` mit `intent="explain"` (kommt ohne `load_item` aus) → `200`, `explanation` gesetzt.
  - Schüler-Principal ohne `student_id` → Request endet als `403` (über das Fehlermodell).
- [ ] ANSWER-Turn-Test (`intent="answer"`, gültiger `item_ref`) erst nach Klärung von `load_item`/`content/items.py` (offene Frage); dann: `grade.confidence == 1.0`, `mastery` gesetzt.
- [ ] Befehl: `uv run pytest tests/test_api_student.py -q` → grün.
- [ ] Befehl: `uv run pytest tests/test_rls.py tests/test_cohort_threshold.py -q` → weiterhin grün (Safety nicht gebrochen).

## Abhängigkeiten

- **AG-1** — `build_graph()`, `TutorState`, `Intent`; ohne den kompilierten LangGraph kann `/turn` nichts ausführen.
- **SAF-2** — `scoped_session`/`require_student_scope` (via `mastery_overview`): erzwingt den fail-closed Scope, auf dem die RLS-Filterung beruht.
- **API-3** — liefert `TurnRequest`/`TurnResponse`/`SkillMastery`/`GradeOut` und das Fehlermodell, das `PermissionError`/`ScopeError` auf `403` mappt.
- Implizit **RET-3** — `mastery_overview` für `/student/mastery`.

**Nachgelagert:** **API-2** (dep: API-1), **FE-S2** (Schüler-Session-Screen), **TST-4** (HTTP-/E2E-Smoke) bauen hierauf auf.

## Definition of Done

- [ ] Akzeptanzkriterien dieses Tasks erfüllt (beide Endpoints, scoped, schonende Sicht).
- [ ] Tests grün inkl. der Safety-Tests (`test_rls.py`, `test_cohort_threshold.py`) — dieser Task ist `safety-critical`.
- [ ] Keine PII in externen LLM-Prompts: der `explain`-Pfad erhält nur Skill-Key/Intent; die API reicht keine Namen durch (P4).
- [ ] `uv`-only, keine `pip`-Aufrufe.
- [ ] GitHub-Issue API-1 geschlossen, E9-Epic-Checkliste aktualisiert.

