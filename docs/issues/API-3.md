## Ziel

Ein gemeinsames Pydantic-Schema-Modul (`api/schemas.py`) und ein einheitliches, zentral registriertes Fehlermodell. Am Ende validiert FastAPI alle Request/Response-Bodies der Schüler- und Lehrer-Endpoints typisiert, und Safety-Ausnahmen (`ScopeError`, `CohortTooSmall`) sowie `LookupError` werden an **einer** Stelle auf neutrale `403`/`404`-Antworten gemappt — ohne Detail-Leaks.

## Kontext & Prinzipien

- **P1 (Safety zuerst, in der DB verankert):** Das Fehlermodell ist die einzige Mapping-Stelle für Safety-Ausnahmen. RLS/Scoping wirft die Exceptions tief im Stack; hier wird verhindert, dass die *Antwort selbst* (z. B. die Kohortengrösse `n=3`) zur Leck-Quelle wird. Neutrale Meldung statt Exception-Text.
- **P5 (Open Learner Model):** `SkillMastery` trägt `uncertainty` als first-class-Feld — die Lehrerseite zeigt es, die Schülerseite nicht. Das Schema macht die Unsicherheit überhaupt erst transportierbar.
- **P4 (PII-Minimierung):** Schemas führen nur IDs/Skill-Keys und Lernstandszahlen, keine Klartext-Profile. `TurnRequest` reicht `subject_key`/`skill_key`, nicht Namen.

## Zu erstellende/ändernde Dateien

- `apps/api/src/its/api/schemas.py` (neu) — alle Request/Response-Modelle.
- `apps/api/src/its/api/errors.py` (neu, empfohlen) — Exception-Handler + `register_error_handlers(app)`.
  > Hinweis: zu entscheiden — der Doc-Text nennt nur "Ein Exception-Handler" ohne Dateinamen. Ein eigenes `errors.py` hält `main.py` schlank und ist isoliert testbar. Alternativ direkt in `main.py`.
- `apps/api/src/its/main.py` (ändern) — `register_error_handlers(app)` aufrufen (Mount der Router erfolgt in API-1/API-2).

## Schnittstellen & Signaturen

Schemas exakt aus `docs/08-backend-api.md` §1 (`Intent` stammt aus `its.agent.state`, AG-1):

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

`Intent` (Referenz aus `its.agent.state`, AG-1 / docs/07 §2):

```python
from enum import StrEnum
class Intent(StrEnum):
    ANSWER = "answer"
    EXPLAIN = "explain"
    HINT = "hint"
    WHY = "why"
    NEXT = "next"
```

Safety-Exceptions, die gemappt werden (aus SAF-2/SAF-3, docs/04):

```python
# its.safety.scoping
class ScopeError(PermissionError): ...
# its.safety.cohort
class CohortTooSmall(PermissionError): ...
```

Fehlermodell (aus docs/08-backend-api.md §1):
> Einheitliches Fehlermodell: `ScopeError`/`CohortTooSmall` → `403`; `LookupError` → `404`; Validierung → `422` (FastAPI default). Ein Exception-Handler mappt die Safety-Exceptions auf `403` mit neutraler Meldung (keine Detail-Leaks).

Vorgeschlagene Handler-Registrierung (FastAPI-Standard-API, nicht erfunden):

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from its.safety.scoping import ScopeError
from its.safety.cohort import CohortTooSmall

def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ScopeError)
    @app.exception_handler(CohortTooSmall)
    async def _forbidden(request: Request, exc: Exception) -> JSONResponse:
        # Exception-Text NUR loggen, niemals serialisieren (kein n=…-Leak)
        return JSONResponse(status_code=403, content={"detail": "forbidden"})

    @app.exception_handler(LookupError)
    async def _not_found(request: Request, exc: LookupError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": "not found"})
```

> Hinweis: zu entscheiden — ob ein Handler für zwei Exception-Typen via gestapelten Dekoratoren registriert werden soll (so wie oben) oder zwei separate Funktionen. Beide Wege sind FastAPI-konform; oben gestapelt zur Knappheit.

## Umsetzungsschritte

- [ ] `apps/api/src/its/api/__init__.py` sicherstellen (Package).
- [ ] `schemas.py` mit den sechs Modellen exakt nach §1 anlegen; `Intent` aus `its.agent.state` importieren (Abhängigkeit zu AG-1).
- [ ] Prüfen, dass `SkillMastery`-Feldnamen exakt den dict-Keys von `mastery_overview` (RET-3) und der Teacher-Roh-Query entsprechen (`skill_id`, `name`, `mastery`, `uncertainty`, `attempts_count`).
- [ ] `errors.py` mit `register_error_handlers(app)` anlegen; Handler für `ScopeError`, `CohortTooSmall` → `403` neutral, `LookupError` → `404`.
- [ ] Sicherstellen, dass der Exception-Text nur ins Log geht (z. B. `logging.getLogger(...).warning(...)`), nie in den Response-Body.
- [ ] `main.py`: `register_error_handlers(app)` in `create_app()` aufrufen.
- [ ] Validierung (`422`) explizit dem FastAPI-Default überlassen — **keinen** eigenen Handler für `RequestValidationError` schreiben.
- [ ] Optional (empfohlen, offene Frage): schlankes `StudentSkillMastery`-Schema ohne `uncertainty` für die schonende Schülersicht vorsehen.

## Akzeptanzkriterien

- [ ] Alle Schemas aus §1 sind vollständig und typisiert vorhanden (`TurnRequest`, `GradeOut`, `TurnResponse`, `SkillMastery`, `CohortStat`).
- [ ] `Intent` wird aus `its.agent.state` importiert (nicht dupliziert).
- [ ] `ScopeError` und `CohortTooSmall` → HTTP `403` mit **neutralem** Body (kein Exception-Text, keine Kohortengrösse).
- [ ] `LookupError` → HTTP `404` neutral.
- [ ] Ein fehlerhafter Request-Body → HTTP `422` (FastAPI-Default, unverändert).
- [ ] `register_error_handlers(app)` ist in `main.py` aktiv.

## Tests / Verifikation

- [ ] `apps/api` → `uv run python -c "from its.api.schemas import TurnRequest, TurnResponse, SkillMastery, CohortStat, GradeOut; print('ok')"` druckt `ok`.
- [ ] Unit-Test (z. B. `tests/test_api_errors.py`) mit FastAPI-`TestClient` und Wegwerf-Routen, die gezielt werfen:
  - Route wirft `ScopeError("student without student_id")` → Response `403`, Body `{"detail":"forbidden"}`, **kein** `student_id`-Text.
  - Route wirft `CohortTooSmall("cohort n=3 below threshold k=10")` → Response `403`, Body enthält **nicht** `n=3`.
  - Route wirft `LookupError` → `404`.
  - POST mit ungültigem JSON-Body gegen ein `TurnRequest`-Endpoint → `422`.
- [ ] Befehl: `uv run pytest tests/test_api_errors.py -q` → grün.

## Abhängigkeiten

- **FND-4** — liefert `its.main.create_app` (App-Factory), `its.config.settings` und das `auth`-Package, in das die Schemas eingebettet werden.
- Implizit **AG-1** — `Intent` wird aus `its.agent.state` importiert; ohne AG-1 fehlt der Enum. (Im Doc als Voraussetzung für E9 gelistet.)
- Implizit **SAF-2/SAF-3** — die zu mappenden Exception-Klassen `ScopeError`/`CohortTooSmall` stammen von dort.

**Nachgelagert:** API-1 und API-2 importieren diese Schemas und verlassen sich auf das Fehlermodell.

## Definition of Done

- [ ] Akzeptanzkriterien dieses Tasks erfüllt (Schemas vollständig, Fehlermodell neutral).
- [ ] Tests grün (`uv run pytest tests/test_api_errors.py -q`); keine Safety-Tests durch diese Änderung gebrochen.
- [ ] Keine PII in externen LLM-Prompts (für diesen Task nicht einschlägig — kein LLM-Call).
- [ ] `uv`-only, keine `pip`-Aufrufe.
- [ ] GitHub-Issue API-3 geschlossen, E9-Epic-Checkliste aktualisiert.

