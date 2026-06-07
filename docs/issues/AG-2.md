## Ziel

Die fünf Knoten des Agent-Loops sind implementiert: `route` wählt Modus/Eskalation, `retrieve` holt Material/Stand über den passenden Modus, `assess` bewertet eine Schülerantwort über den **kuratierten** Grader, `update_model` schreibt das Resultat via `record_attempt` ins Learner-Modell (nur bei hoher Konfidenz), und `explain` erzeugt eine generative Erklärung aus rein anonymisiertem Kontext.

## Kontext & Prinzipien

- **P2 (kuratierte Bewertung):** `assess_node` lädt das kuratierte `Item` (inkl. `answer_key`) und ruft `grader.grade(answer, item)`. Der `answer_key` stammt aus der Kuratierung, **nie** vom LLM. Ein LLM, das den Schlüssel halluziniert, würde ein Kind falsch unterrichten — deshalb ist dieser Pfad strikt generativ-frei.
- **P3 (Modell verbessert sich):** `update_model_node` aktualisiert `learner_state` ausschliesslich über `record_attempt` — nicht durch direktes Schreiben und nicht durch Agent-„Selbstverbesserung". Mastery/Unsicherheit bleiben konsistent.
- **P6 (Mensch im Loop):** `update_model_node` zementiert **nur bei `confidence >= 0.9`**. Niedrige Konfidenz (z. B. History-Grader < 1.0) wird nicht automatisch geschrieben, sondern bleibt für Lehrer-Review offen — Sicherheitsarchitektur, kein Reporting.
- **P4 (keine PII extern):** `explain_node` baut den Prompt **nur** aus `skill_key` und `intent` (ggf. anonymisierter Fehlerart) — kein Name, kein Geburtsdatum. Der eigentliche scrub-Schutz liegt in AG-3, aber `explain_node` füttert ohnehin nur IDs/Keys.
- **P1 (Safety in der DB):** Der Schreibpfad in `update_model_node` muss innerhalb der RLS-gescopten Session laufen — eine fehlerhafte Query darf keine fremden Zeilen berühren.

## Zu erstellende/ändernde Dateien

- `apps/api/src/its/agent/nodes/route.py` — `route_node`.
- `apps/api/src/its/agent/nodes/retrieve.py` — `retrieve_node`.
- `apps/api/src/its/agent/nodes/assess.py` — `assess_node` (kuratiert, P2).
- `apps/api/src/its/agent/nodes/update_model.py` — `update_model_node` (P3/P6).
- `apps/api/src/its/agent/nodes/explain.py` — `explain_node` (generativ, P4).

## Schnittstellen & Signaturen

`nodes/route.py`:

```python
from its.agent.state import TutorState, Intent
from its.retrieval.router import route, Mode

def route_node(state: TutorState) -> TutorState:
    has_scope = bool(state.student_id)
    if state.intent in (Intent.ANSWER, Intent.NEXT):
        decision = route("student progress", has_student_scope=has_scope)  # tendiert INDIVIDUAL
    else:
        decision = route(state.skill_key, has_student_scope=has_scope)     # tendiert SEMANTIC
    state.route_reason = f"{decision.mode}:{decision.reason}"
    return state
```

`nodes/assess.py` — **kuratiert (P2):**

```python
from its.agent.state import TutorState
from its.grading.registry import get_grader
from its.grading.base import Item
from its.content.items import load_item   # lädt kuratiertes Item inkl. answer_key

def assess_node(state: TutorState) -> TutorState:
    if state.answer is None or state.item_ref is None:
        return state
    item: Item = load_item(state.item_ref)        # answer_key ist kuratiert, NICHT vom LLM
    grader = get_grader(state.subject_key)
    result = grader.grade(state.answer, item)
    state.grade = {"correct": result.correct, "feedback": result.feedback,
                   "confidence": result.confidence}
    return state
```

Referenz (aus GR-1, damit der Body autark ist):

```python
@dataclass(frozen=True)
class Item:
    skill_key: str
    prompt: str
    answer_key: str          # KURATIERT (P2)
    rubric: str | None = None

@dataclass(frozen=True)
class GradeResult:
    correct: bool
    feedback: str
    confidence: float        # 1.0 = deterministisch geprüft

def get_grader(subject_key: str) -> GraderStrategy: ...
```

`nodes/update_model.py` — **Modell aktualisiert sich (P3), Konfidenz-Gate (P6):**

```python
from its.agent.state import TutorState
from its.learner_model.tracing import record_attempt
from its.db.models import Attempt
from its.db.session import SessionLocal  # innerhalb scoped_session aufgerufen

def update_model_node(state: TutorState) -> TutorState:
    if state.grade is None:
        return state
    # WICHTIG: nur zementieren, wenn Konfidenz hoch genug (sonst Lehrer-Review, P6)
    if state.grade["confidence"] >= 0.9:
        with SessionLocal() as s:   # in der Praxis: die request-scoped Session injizieren
            s.add(Attempt(student_id=state.student_id, skill_id=_skill_id(state.skill_key),
                          item_ref=state.item_ref, is_correct=state.grade["correct"],
                          raw_answer=state.answer))
            ls = record_attempt(s, state.student_id, _skill_id(state.skill_key),
                                state.grade["correct"])
            state.mastery = ls.mastery
            s.commit()
    return state
```

Referenz (aus LM-2):

```python
def record_attempt(session, student_id, skill_id, correct: bool,
                   params: BKTParams | None = None) -> LearnerState: ...
```

`nodes/explain.py` — **generativer Pfad (fehlertolerant, P4):**

```python
from its.agent.state import TutorState
from its.llm.client import complete
from its.llm.prompts import EXPLAIN_SYSTEM

def explain_node(state: TutorState) -> TutorState:
    # NUR anonymisierter Kontext (P4): skill_key, Intent, ggf. letzte Fehlerart — kein Name.
    prompt = f"Skill: {state.skill_key}. Modus: {state.intent}. Formuliere eine kurze, andere Erklärung."
    state.explanation = complete(system=EXPLAIN_SYSTEM, user=prompt)
    return state
```

`nodes/retrieve.py`: ruft je nach `route` `semantic`/`individual`/`population` auf und legt Ergebnisse in `state.retrieved` ab.

## Umsetzungsschritte

- [ ] `route_node`: `has_scope = bool(state.student_id)`; ANSWER/NEXT → `route("student progress", …)`, sonst `route(state.skill_key, …)`; `state.route_reason = f"{decision.mode}:{decision.reason}"`.
- [ ] `assess_node`: Guard (`answer is None or item_ref is None` → unverändert zurück).
- [ ] `assess_node`: `load_item(item_ref)` → `Item`; `get_grader(subject_key)`; `grader.grade(answer, item)`; `state.grade` als Dict mit `correct/feedback/confidence` setzen.
- [ ] `update_model_node`: Guard (`state.grade is None` → unverändert zurück).
- [ ] `update_model_node`: nur bei `state.grade["confidence"] >= 0.9` schreiben; `Attempt` anlegen, `record_attempt` aufrufen, `state.mastery = ls.mastery`, `commit`.
- [ ] `_skill_id(skill_key) -> uuid`-Helper implementieren (Lookup `skills.key` → `skills.id`).
- [ ] Session: innerhalb der RLS-gescopten Session laufen lassen (request-scoped Session injizieren statt freier `SessionLocal()`); Vorgehen dokumentieren.
- [ ] `explain_node`: Prompt **nur** aus `skill_key` + `intent`; `complete(system=EXPLAIN_SYSTEM, user=prompt)`; `state.explanation` setzen.
- [ ] `retrieve_node`: Modus aus `route` bestimmen, passenden Modus (`semantic`/`individual`/`population`) aufrufen, Ergebnis in `state.retrieved`.
- [ ] Sicherstellen, dass kein Node-Pfad freien Schülertext (z. B. `raw_answer`) an das LLM gibt.

> Hinweis: zu entscheiden — `content/items.py::load_item` ist in den Docs referenziert, aber weder Datei noch Signatur sind spezifiziert. Quelle des kuratierten `answer_key` (DB-Tabelle / Vault-Frontmatter) klären, bevor `assess_node` final wird.
> Hinweis: zu entscheiden — Auflösung `skill_key → skill_id` (`_skill_id`): genauer Lookup-Pfad (`skills.key`, ggf. mit `subject_id`-Scope) festlegen.
> Hinweis: zu entscheiden — wie die request-scoped, RLS-gescopte Session in `update_model_node` injiziert wird (Closure über `build_graph`, State-Feld, ContextVar).

## Akzeptanzkriterien

- [ ] `assess_node` nutzt den **kuratierten** Grader (`get_grader` + `load_item.answer_key`); keine LLM-Generierung des Schlüssels (P2).
- [ ] `update_model_node` schreibt via `record_attempt` und legt `Attempt` an; `state.mastery` wird gesetzt (P3).
- [ ] Niedrige Grader-Konfidenz (`< 0.9`) wird **nicht** automatisch zementiert; `learner_state` bleibt unverändert (P6).
- [ ] `explain_node` erhält nur anonymisierten Kontext (`skill_key` + `intent`), keinen Namen (P4).
- [ ] `route_node` setzt `route_reason` aus der `RouteDecision`; ANSWER/NEXT tendiert INDIVIDUAL, sonst SEMANTIC.
- [ ] Der Schreibpfad läuft innerhalb der RLS-gescopten Session (P1).

## Tests / Verifikation

- [ ] Konfidenz-Gate (Unit): `update_model_node` mit Fake-`state.grade = {"correct": True, "feedback": "", "confidence": 0.5}` → kein DB-Write, `state.mastery is None`.
- [ ] Voller ANSWER-Turn (Integration, gegen Test-DB mit RLS): `uv run pytest tests/test_agent_turn.py -q` → `result.grade["confidence"] == 1.0` und `result.mastery is not None`.
- [ ] `route_node`-Logik (Unit): `Intent.ANSWER` → `route_reason` beginnt mit `individual`; `Intent.WHY` → beginnt mit `semantic`.
- [ ] `explain_node` (Unit, gemockter `complete`): übergebener `user`-Prompt enthält keinen Personennamen; `state.explanation` gesetzt.

## Abhängigkeiten

- **AG-1** — liefert `TutorState`/`Intent` und das Graphgerüst, in das diese Nodes eingehängt werden.
- **RET-1** (`route`, `RouteDecision`, `Mode`) — `route_node` und `retrieve_node` konsumieren den Router.
- **LM-2** (`record_attempt`) — `update_model_node` schreibt darüber.
- **GR-1** (`get_grader`, `Item`, `GradeResult`) — `assess_node` bewertet darüber.
- **AG-3** (`llm/client.complete`, `EXPLAIN_SYSTEM`) — `explain_node` ruft den anonymisierenden LLM-Client.
- **Nachgelagert:** API-1/E9 (ruft den Loop hinter `/student/turn`), TST-3/E12 (`test_agent_turn.py`).

## Definition of Done

- [ ] Akzeptanzkriterien dieses Tasks erfüllt.
- [ ] Tests grün, inkl. Safety-Bezug: der `update_model`-Schreibpfad läuft RLS-gescopt; Konfidenz-Gate-Test grün.
- [ ] Keine PII in externen LLM-Prompts: `explain_node` gibt nur Skill-Key/Intent weiter.
- [ ] `uv`-only, keine `pip`-Aufrufe.
- [ ] GitHub-Issue AG-2 geschlossen, E8-Epic-Checkliste aktualisiert.
