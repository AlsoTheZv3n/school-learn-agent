## Ziel

`tests/test_agent_turn.py` fährt einen **vollständigen `ANSWER`-Turn** end-to-end gegen die Test-DB (innerhalb `db_factory.as_student(...)`) und beweist operativ: die Bewertung ist deterministisch (`grade["confidence"] == 1.0`, kuratiert, P2) und das **Learner-Modell** wurde aktualisiert (`mastery is not None`, P3).

## Kontext & Prinzipien

- **P2 (Kuratierte Antworten):** Der `assess`-Node nutzt den **kuratierten** Grader; der Test verankert das, indem er `confidence == 1.0` prüft — der Bewertungspfad halluziniert nicht.
- **P3 (Das Learner-Modell verbessert sich, nicht der Agent):** `update_model` schreibt via `record_attempt` ins `learner_state`; der Test prüft, dass sich **`mastery`** ändert — das auditierbare Modell mutiert, nicht der Agent.
- **P6 (Mensch im Loop ist Sicherheitsarchitektur):** `update_model_node` zementiert nur bei `confidence >= 0.9`; niedrige Konfidenz geht in Lehrer-Review, nicht automatisch ins Modell. (Optional als Negativfall testen.)
- **P1 (RLS):** Der Turn läuft in einer scoped Session (`db_factory.as_student(student.id)`) — der Schreibpfad respektiert die Zeilenisolation.

## Zu erstellende/ändernde Dateien

- `tests/test_agent_turn.py` — neu.
- `tests/conftest.py` — ggf. erweitern um `seeded_student_and_item` (falls nicht in TST-1 verortet).

> Hinweis: zu entscheiden — `seeded_student_and_item` ist in docs/10 §5 vorausgesetzt, aber nirgends definiert. Ebenso ist `load_item`/`content/items.py` (von `assess_node` benutzt) in keinem Doc spezifiziert. Beides muss bereitgestellt oder gemockt werden, sonst läuft der Turn nicht.

## Schnittstellen & Signaturen

**State** (`apps/api/src/its/agent/state.py`, docs/07 §2 — autark):

```python
from dataclasses import dataclass, field
from enum import StrEnum

class Intent(StrEnum):
    ANSWER = "answer"
    EXPLAIN = "explain"
    HINT = "hint"
    WHY = "why"
    NEXT = "next"

@dataclass
class TutorState:
    student_id: str
    subject_key: str
    skill_key: str
    intent: Intent
    answer: str | None = None
    item_ref: str | None = None
    retrieved: list[dict] = field(default_factory=list)
    grade: dict | None = None
    mastery: float | None = None
    explanation: str | None = None
    route_reason: str | None = None
```

**Graph** (`apps/api/src/its/agent/graph.py`, docs/07 §3): `build_graph()` kompiliert `route → retrieve → conditional(assess → update_model | explain) → END`. `assess_node` lädt das Item via `load_item(item_ref)` und ruft `get_grader(subject_key).grade(answer, item)`. `update_model_node` schreibt nur bei `confidence >= 0.9` einen `Attempt` und ruft `record_attempt(...)`, setzt `state.mastery = ls.mastery`.

`tests/test_agent_turn.py` (docs/10 §5 — autark):

```python
def test_answer_turn_updates_mastery(db_factory, seeded_student_and_item):
    student, item_ref, skill_key = seeded_student_and_item
    from its.agent.graph import build_graph
    from its.agent.state import TutorState, Intent
    graph = build_graph()
    with db_factory.as_student(student.id):
        state = TutorState(student_id=str(student.id), subject_key="math",
                           skill_key=skill_key, intent=Intent.ANSWER,
                           answer="x**2 + 2*x + 1", item_ref=item_ref)
        result = graph.invoke(state)
    assert result.grade is not None
    assert result.grade["confidence"] == 1.0     # kuratiert (P2)
    assert result.mastery is not None            # Modell wurde aktualisiert (P3)
```

`record_attempt` (`apps/api/src/its/learner_model/tracing.py`, docs/06 A.2): aktualisiert/anlegt `LearnerState(mastery, uncertainty, attempts_count)` und gibt es zurück.

## Umsetzungsschritte

- [ ] `seeded_student_and_item`-Fixture bereitstellen: Schüler + Skill (`subject = math`) + kuratiertes Item (`item_ref`, `answer_key = "x**2 + 2*x + 1"`) anlegen; Rückgabe `(student, item_ref, skill_key)`.
- [ ] Sicherstellen, dass die Grader-Registry beim Test-Lauf gefüllt ist (Import von `its.grading` registriert `MathGrader`).
- [ ] `load_item(item_ref)` verfügbar machen: entweder aus `content/items.py` (falls vorhanden) oder im Test via `monkeypatch` auf ein Item mit dem kuratierten `answer_key` setzen.
- [ ] **Session-Injektion klären:** `update_model_node` öffnet im Doc-Stub `SessionLocal()`. Damit der Schreibpfad die Test-Session/den RLS-Kontext nutzt, die request-scoped Session injizieren (oder den Node so konfigurieren, dass er die `db_factory.as_student`-Session verwendet).
- [ ] `test_agent_turn.py` mit dem Happy-Path-Test (oben) anlegen.
- [ ] **Negativfall (P6, optional):** ein Turn mit Grader-Konfidenz < 0.9 (z. B. History-Grader-Pfad oder gemockte niedrige Konfidenz) darf `learner_state` **nicht** zementieren.
- [ ] **Commit/Rollback-Konflikt lösen:** `update_model_node` ruft `commit()`. Sicherstellen, dass der Test danach aufräumt (eigene Session + explizites Teardown oder Savepoint), damit nachfolgende Tests isoliert bleiben.

## Akzeptanzkriterien

- [ ] Ein voller `ANSWER`-Turn läuft `route → retrieve → assess → update_model → END` durch.
- [ ] `result.grade is not None` und `result.grade["confidence"] == 1.0` (kuratiert, P2).
- [ ] `result.mastery is not None` — das Learner-Modell wurde aktualisiert (P3).
- [ ] Der Turn läuft in einer scoped Session (`db_factory.as_student`) und respektiert RLS.
- [ ] (Optional) Niedrige Grader-Konfidenz (< 0.9) wird **nicht** automatisch zementiert (P6).

## Tests / Verifikation

```bash
docker compose -f infra/docker-compose.yml up -d
export DATABASE_URL=postgresql+psycopg://its:its_dev_pw@localhost:5432/its
cd apps/api && uv sync
uv run pytest tests/test_agent_turn.py -q
```

Erwartet: `1 passed` (bzw. 2 mit Negativfall). Konkret: `result.grade["confidence"] == 1.0` und `result.mastery is not None`. Bei korrekter Antwort steigt die Mastery gegenüber dem `p_init`-Default (0.2). Ein anschliessender `SELECT count(*) FROM attempts` in derselben Schüler-Session zeigt genau den eben geschriebenen Versuch (RLS-gescoped).

## Abhängigkeiten

- **AG-2 (Agent-Nodes):** liefert `route/retrieve/assess/update_model/explain` und den kompilierten Graph — der Testgegenstand.
- **TST-1 (Fixtures):** liefert `db_factory` und die Test-DB; ohne sie kein scoped Turn gegen Postgres.
- (implizit) GR-2 (Math-Grader), LM-2 (`record_attempt`), DB-3 (`scoped_session`-Mechanik).
- **Nachgelagert:** TST-4 (E2E-Smoke) prüft denselben Pfad zusätzlich über die HTTP-API.

## Definition of Done

- [ ] Akzeptanzkriterien aus docs/10 §8 (Integration): Agent-Turn-Test mit Konfidenz 1.0 + Mastery aktualisiert.
- [ ] Tests grün, inkl. der Safety-Tests (weiterhin grün).
- [ ] Keine PII in externen LLM-Prompts — der `ANSWER`-Turn nutzt den kuratierten Grader (kein externer LLM-Call); falls `explain` mitgetestet wird, läuft es durch `scrub` (P4).
- [ ] `uv`-only, keine `pip`-Aufrufe.
- [ ] Zugehöriges GitHub-Issue (TST-3) geschlossen, Epic-Checkliste (E12) aktualisiert.
