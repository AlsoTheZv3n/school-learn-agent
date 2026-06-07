# 07 — Agent-Loop (E8, M3)

**Ziel:** Der pädagogische Loop als LangGraph-State-Machine. `assess` nutzt den kuratierten
Grader (P2), `explain` ist der generative Pfad. Der LLM-Client anonymisiert PII vor jedem
externen Call (P4).

**Voraussetzungen:** RET-1 (Router), LM-2 (Tracing), GR-1 (Grader-Registry), FND-4.
**Issues:** AG-1 … AG-3.

---

## 1. Loop-Überblick

```
        ┌──────────────────────────── student answer / request ───────────────────────────┐
        ▼                                                                                  │
   [route] ──► [retrieve] ──► (Frage?) ──► [assess] ──► [update_model] ──► nächster Schritt
        │                          │                                                       
        └────────► (Erklärung/Hint?) ────────► [explain]  (generativ, P2) ─────────────────┘
```

- `route`: Modus + Eskalation (nutzt `retrieval/router.py`).
- `retrieve`: holt Material/Stand über den passenden Modus (RLS/Cohort beachtet).
- `assess`: bewertet eine Schülerantwort über den **kuratierten** Grader (P2).
- `update_model`: schreibt das Resultat via `record_attempt` ins Learner-Modell (P3).
- `explain`: erzeugt eine **Erklärung/Umformulierung** (generativer, fehlertoleranter Pfad).

---

## 2. State (AG-1)

`apps/api/src/its/agent/state.py`:

```python
from dataclasses import dataclass, field
from enum import StrEnum

class Intent(StrEnum):
    ANSWER = "answer"          # Schüler:in reicht eine Antwort ein -> assess
    EXPLAIN = "explain"        # "anders erklären"
    HINT = "hint"              # "Hinweis"
    WHY = "why"                # "wozu lerne ich das"
    NEXT = "next"              # nächste Frage anfordern

@dataclass
class TutorState:
    student_id: str
    subject_key: str
    skill_key: str
    intent: Intent
    answer: str | None = None
    item_ref: str | None = None
    # Ergebnisse, von Nodes befüllt:
    retrieved: list[dict] = field(default_factory=list)
    grade: dict | None = None
    mastery: float | None = None
    explanation: str | None = None
    route_reason: str | None = None
```

---

## 3. Nodes (AG-2)

`apps/api/src/its/agent/nodes/route.py`:

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

`apps/api/src/its/agent/nodes/assess.py` — **kuratiert (P2):**

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

`apps/api/src/its/agent/nodes/update_model.py` — **Modell aktualisiert sich (P3):**

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

`apps/api/src/its/agent/nodes/explain.py` — **generativer Pfad (fehlertolerant):**

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

`apps/api/src/its/agent/nodes/retrieve.py`: ruft je nach `route` `semantic`/`individual`/
`population` auf und legt Ergebnisse in `state.retrieved` ab.

### Graph-Verdrahtung

`apps/api/src/its/agent/graph.py`:

```python
from langgraph.graph import StateGraph, END
from its.agent.state import TutorState, Intent
from its.agent.nodes.route import route_node
from its.agent.nodes.retrieve import retrieve_node
from its.agent.nodes.assess import assess_node
from its.agent.nodes.update_model import update_model_node
from its.agent.nodes.explain import explain_node

def build_graph():
    g = StateGraph(TutorState)
    g.add_node("route", route_node)
    g.add_node("retrieve", retrieve_node)
    g.add_node("assess", assess_node)
    g.add_node("update_model", update_model_node)
    g.add_node("explain", explain_node)

    g.set_entry_point("route")
    g.add_edge("route", "retrieve")

    def branch(state: TutorState) -> str:
        return "assess" if state.intent == Intent.ANSWER else "explain"
    g.add_conditional_edges("retrieve", branch, {"assess": "assess", "explain": "explain"})
    g.add_edge("assess", "update_model")
    g.add_edge("update_model", END)
    g.add_edge("explain", END)
    return g.compile()
```

---

## 4. LLM-Client + Anonymisierung (AG-3) · `safety-critical`

`apps/api/src/its/llm/anonymize.py`:

```python
import re

# Vor JEDEM externen Call anzuwenden. Defense-in-depth zusätzlich dazu:
# dem LLM werden ohnehin nur IDs/Skill-Keys übergeben, keine Namen.
_PATTERNS = [
    (re.compile(r"\b[A-ZÄÖÜ][a-zäöü]+\s[A-ZÄÖÜ][a-zäöü]+\b"), "[NAME]"),
    (re.compile(r"\b\d{2}\.\d{2}\.\d{4}\b"), "[DATE]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[EMAIL]"),
]

def scrub(text: str) -> str:
    for pat, repl in _PATTERNS:
        text = pat.sub(repl, text)
    return text
```

`apps/api/src/its/llm/client.py`:

```python
from its.config import settings
from its.llm.anonymize import scrub

def complete(system: str, user: str) -> str:
    user = scrub(user)               # P4: PII raus, bevor irgendetwas die Maschine verlässt
    if settings.llm_backend == "frontier":
        return _complete_frontier(system, user)   # API-Call; user ist bereits gescrubbt
    return _complete_local(system, user)           # lokales Modell (Qwen2.5 o. Ä.)
```

`apps/api/src/its/llm/prompts/__init__.py`: Konstanten wie `EXPLAIN_SYSTEM` (Ton:
altersgerecht, knapp, ermutigend; keine endgültigen Bewertungen — die kommen aus `assess`).

**AK:** Jeder externe Call läuft durch `scrub`; Backend per `settings.llm_backend` umschaltbar;
dem LLM werden ohnehin nur IDs/Skill-Keys gereicht.

---

## 5. Akzeptanzkriterien (gesamt)

- [ ] `TutorState` + `Intent` definiert (AG-1)
- [ ] Graph: route → retrieve → (assess→update_model | explain) → END (AG-1)
- [ ] `assess` nutzt kuratierten Grader; `update_model` schreibt via `record_attempt` (AG-2, P2/P3)
- [ ] niedrige Grader-Konfidenz wird **nicht** automatisch zementiert (P6)
- [ ] `explain` erhält nur anonymisierten Kontext (AG-2, P4)
- [ ] `llm/client.py` scrubbt vor externem Call; Backend umschaltbar (AG-3)

---

## Claude-Code-Prompt

```
Setze E8 (docs/07-agent.md) um: agent/state.py (TutorState, Intent), agent/nodes/{route,
retrieve,assess,update_model,explain}.py und agent/graph.py (LangGraph: route→retrieve→
conditional(assess→update_model | explain)→END). assess MUSS den kuratierten Grader nutzen,
update_model schreibt via record_attempt und zementiert nur bei Konfidenz >= 0.9. Implementiere
llm/anonymize.py (scrub) und llm/client.py (scrub vor jedem externen Call, Backend per settings)
sowie llm/prompts/. Schreibe einen Integrationstest für einen vollen ANSWER-Turn gegen die
Test-DB (Frage→Antwort→Mastery-Update). Halte P2/P3/P4/P6 ein. Schliesse AG-1..3.
```
