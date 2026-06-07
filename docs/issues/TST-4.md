## Ziel

Ein **E2E-Smoke** beweist den gesamten Pfad über die HTTP-API: Login → Session → Antwort → Mastery sichtbar → Lehrer sieht den Stand. Der HTTP-Smoke (mit `httpx`) ist **zwingend**; ein Browser-E2E (Playwright) ist optional je nach Reifegrad. Zentral: die **Präsentations-Trennung** (Lehrer sieht `uncertainty`, Schüler nicht, P5).

## Kontext & Prinzipien

- **P5 (Open Learner Model):** Der Smoke prüft, dass `GET /student/mastery` die schonende Sicht (nur `mastery`) liefert, während `GET /teacher/student/{id}/mastery` zusätzlich `uncertainty` enthält. Genau die Trennung „zwei Sichten, eine Wahrheit".
- **P1 (RLS):** Der Lehrer-Endpoint ist RLS-gefiltert (`teacher_*_in_class`) — der Smoke nutzt einen Lehrer, dessen Klasse den Schüler enthält, und prüft konsistente Werte; eine kleine Kohorte liefert `403` (Min-Cohort sichtbar gemacht).
- **P2/P3:** Der `POST /student/turn` fährt den Agent-Loop; der Smoke sieht denselben deterministischen Grade (Konfidenz 1.0) und die gestiegene Mastery wie TST-3, jetzt über die API-Grenze.

## Zu erstellende/ändernde Dateien

- `tests/e2e/__init__.py` — neu (Package-Marker).
- `tests/e2e/test_http_smoke.py` — neu (HTTP-Smoke, zwingend).
- `tests/e2e/test_browser_smoke.py` — optional (Playwright, je nach Reifegrad).
- `apps/web/` — Frontend (FE-T2 liefert das Lehrer-Panel) für den optionalen Browser-Pfad.

> Hinweis: zu entscheiden — `current_principal` ist in FND-5 ein Stub (`NotImplementedError`). Für den HTTP-Smoke braucht es eine testbare Auth: entweder FastAPI `dependency_overrides` mit Test-Principals oder ein Test-JWT gegen `settings.jwt_public_key`. Token-Herkunft im Plan offen.

## Schnittstellen & Signaturen

**Endpoints** (docs/08 — autark):

```python
# apps/api/src/its/api/student.py
@router.post("/turn", response_model=TurnResponse)
def turn(req: TurnRequest, principal=Depends(current_principal)) -> TurnResponse: ...

@router.get("/mastery", response_model=list[SkillMastery])
def my_mastery(principal=Depends(current_principal)) -> list[SkillMastery]: ...

# apps/api/src/its/api/teacher.py
@router.get("/student/{student_id}/mastery", response_model=list[SkillMastery])
def student_mastery(student_id: str, principal=Depends(current_principal)): ...

@router.get("/class/{class_id}/skill/{skill_id}/distribution", response_model=CohortStat)
def class_distribution(class_id: str, skill_id: str, principal=Depends(current_principal)): ...
```

**Schemas** (docs/08 §1 — autark):

```python
class TurnRequest(BaseModel):
    subject_key: str
    skill_key: str
    intent: Intent
    answer: str | None = None
    item_ref: str | None = None

class TurnResponse(BaseModel):
    grade: GradeOut | None = None       # {correct, feedback, confidence}
    mastery: float | None = None
    explanation: str | None = None
    route_reason: str | None = None

class SkillMastery(BaseModel):
    skill_id: str
    name: str
    mastery: float
    uncertainty: float          # Lehrerseite zeigt das (P5)
    attempts_count: int

class CohortStat(BaseModel):
    n: int
    avg_mastery: float
```

**Fehlermodell** (docs/08 §1): `ScopeError`/`CohortTooSmall` → `403` (neutral); `LookupError` → `404`; Validierung → `422`.

**Frontend-Client** (`apps/web/src/api/client.ts`, docs/09 §1 — für den optionalen Browser-Pfad):

```ts
export type Intent = "answer" | "explain" | "hint" | "why" | "next";
export interface TurnResponse {
  grade?: { correct: boolean; feedback: string; confidence: number };
  mastery?: number;
  explanation?: string;
  route_reason?: string;
}
export const turn = (body: {subject_key:string; skill_key:string; intent:Intent; answer?:string; item_ref?:string}, t:string) =>
  post<TurnResponse>("/student/turn", body, t);
```

HTTP-Smoke-Skizze (docs/10 §6):

```python
import httpx

def test_http_smoke(api_base, student_token, teacher_token, seeded_class):
    student_id, class_id, skill_id, item_ref = seeded_class
    c = httpx.Client(base_url=api_base)
    # 1) Schüler beantwortet eine Aufgabe
    r = c.post("/student/turn", headers={"Authorization": f"Bearer {student_token}"},
               json={"subject_key": "math", "skill_key": "expand",
                     "intent": "answer", "answer": "x**2 + 2*x + 1", "item_ref": item_ref})
    assert r.status_code == 200
    assert r.json()["grade"]["confidence"] == 1.0   # kuratiert (P2)
    # 2) Schüler-Mastery: KEINE uncertainty nach aussen (P5)
    r2 = c.get("/student/mastery", headers={"Authorization": f"Bearer {student_token}"})
    assert r2.status_code == 200
    # 3) Lehrer sieht denselben Schüler INKL. uncertainty (P5), RLS-gefiltert
    r3 = c.get(f"/teacher/student/{student_id}/mastery",
               headers={"Authorization": f"Bearer {teacher_token}"})
    assert r3.status_code == 200
    assert "uncertainty" in r3.json()[0]
```

## Umsetzungsschritte

- [ ] `tests/e2e/`-Package anlegen.
- [ ] Test-Auth bereitstellen: `dependency_overrides` für `current_principal` mit Test-Schüler/-Lehrer **oder** Test-JWT generieren; Token-Fixtures `student_token`/`teacher_token`.
- [ ] Seed-Fixture `seeded_class`: Schüler + Lehrer + Klasse + Enrollment + Skill + kuratiertes Item, so dass RLS den Lehrer den Schüler sehen lässt und der Math-Grader bewerten kann.
- [ ] API für den Smoke starten (laufende Instanz oder `httpx.ASGITransport` gegen `its.main:app`).
- [ ] HTTP-Smoke implementieren: `POST /student/turn` → 200, `grade.confidence == 1.0`; `GET /student/mastery` → 200 (schonende Sicht); `GET /teacher/student/{id}/mastery` → 200 mit `uncertainty`.
- [ ] **Konsistenz prüfen:** der vom Lehrer gesehene `mastery`-Wert entspricht dem, der dem Schüler angezeigt wird (gleiche `learner_state`-Zeile).
- [ ] **Min-Cohort sichtbar (optional):** `GET /teacher/class/{id}/skill/{id}/distribution` mit kleiner Kohorte ⇒ `403`.
- [ ] (Optional, Browser) Playwright: Schüler beantwortet Aufgabe, Mastery-Bar steigt; Lehrer-Panel zeigt Unsicherheit; kleine Kohorte zeigt „zu wenige Lernende".

## Akzeptanzkriterien

- [ ] HTTP-Smoke grün: Login → `POST /student/turn` → `GET /student/mastery` → `GET /teacher/student/{id}/mastery`.
- [ ] `POST /student/turn` liefert `grade.confidence == 1.0` (P2) und eine `mastery` (P3).
- [ ] Schüler-Mastery-Antwort enthält **kein** `uncertainty`; Lehrer-Antwort enthält `uncertainty` (P5).
- [ ] Lehrer sieht nur Schüler seiner Klasse (RLS-gefiltert, P1); Werte sind konsistent zur Schülersicht.
- [ ] (Optional) Kleine Kohorte → `403` „zu wenige Lernende".
- [ ] (Optional) Browser-E2E zeigt steigende Mastery-Bar und Lehrer-Panel mit Unsicherheit.

## Tests / Verifikation

```bash
docker compose -f infra/docker-compose.yml up -d
export DATABASE_URL=postgresql+psycopg://its:its_dev_pw@localhost:5432/its
cd apps/api && uv sync
# optional API live:
uv run uvicorn its.main:app &
curl -s localhost:8000/health   # -> {"status":"ok"}
uv run pytest tests/e2e/ -q
```

Erwartet: HTTP-Smoke `passed`. Konkret: `POST /student/turn` → `200`, JSON `grade.confidence == 1.0`; `GET /student/mastery` → `200` ohne `uncertainty`-Feld nach aussen; `GET /teacher/student/{id}/mastery` → `200` mit `uncertainty` im ersten Element; kleine Kohorte → `403`.

## Abhängigkeiten

- **API-2 (Teacher-Endpoints):** liefert `GET /teacher/student/{id}/mastery` (inkl. `uncertainty`) und den Kohorten-Endpoint — Kern des Smoke.
- **FE-T2 (Learner-Model-Panel):** liefert die Lehrer-Sicht (Mastery + Unsicherheit) für den optionalen Browser-E2E.
- **TST-1 (Fixtures):** liefert die Test-DB/Seed-Basis; (implizit) API-1 (`POST /student/turn`, `GET /student/mastery`).
- **Nachgelagert:** Schliesst die Pyramide ab; kein weiterer E12-Task hängt hieran.

## Definition of Done

- [ ] Akzeptanzkriterien aus docs/10 §8 (E2E): E2E-Smoke (HTTP mindestens) grün.
- [ ] Tests grün, inkl. der Safety-Tests (weiterhin grün).
- [ ] Keine PII in externen LLM-Prompts — der getestete `ANSWER`-Pfad ist kuratiert; falls `explain` berührt wird, läuft es durch `scrub` (P4).
- [ ] `uv`-only, keine `pip`-Aufrufe.
- [ ] Zugehöriges GitHub-Issue (TST-4) geschlossen, Epic-Checkliste (E12) aktualisiert.
