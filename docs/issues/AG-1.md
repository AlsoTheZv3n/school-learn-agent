## Ziel

Das Zustandsschema des pädagogischen Agenten und der kompilierte LangGraph-Graph stehen: `TutorState` + `Intent` sind definiert, und `build_graph()` verdrahtet die fünf Knoten zu `route → retrieve → conditional(assess → update_model | explain) → END`. Das Graphgerüst kompiliert ohne Fehler und ist die Grundlage, auf der AG-2 die Knotenlogik füllt.

## Kontext & Prinzipien

- **P3 (das Learner-Modell verbessert sich, nicht der Agent):** Der Graph macht das Agentenverhalten zu einer *expliziten, deterministischen* Funktion des Zustands. Es gibt keine selbst-mutierende LLM-Schleife — der State-Graph ist fix, nur `learner_state` ändert sich (in AG-2). Das State-Schema muss daher alle Entscheidungs-Inputs (`intent`, `skill_key`, `student_id`) und alle Node-Ergebnisse (`grade`, `mastery`, `route_reason`) sichtbar tragen.
- **P2 (kuratiert vs. generativ):** Die bedingte Kante nach `retrieve` trennt strukturell den Bewertungspfad (`ANSWER → assess`) vom generativen Pfad (`explain`). Diese Trennung wird hier im Graphen verankert, damit ein LLM nie eine korrekt/falsch-Entscheidung beeinflussen kann.
- **P6 (Mensch im Loop, auditierbar):** Ein expliziter State-Graph mit benannten Knoten und einem `route_reason`-Feld macht das Routing nachvollziehbar — Voraussetzung für spätere Lehrer-Aufsicht.
- **P7 (eine Implementierung):** Der Agent-Loop ist **keine** Plugin-Naht. Genau ein Graph, flach gehalten.

## Zu erstellende/ändernde Dateien

- `apps/api/src/its/agent/state.py` — `Intent` (StrEnum), `TutorState` (dataclass).
- `apps/api/src/its/agent/graph.py` — `build_graph()` (StateGraph-Verdrahtung, kompiliert).
- `apps/api/src/its/agent/__init__.py` und `apps/api/src/its/agent/nodes/__init__.py` — Paket-Init (sofern noch nicht vorhanden).

> Hinweis: `graph.py` importiert die fünf Node-Funktionen aus `agent/nodes/` (AG-2). Für ein eigenständig kompilierbares Gerüst entweder AG-2 zuvor/parallel anlegen oder die Nodes zunächst als minimale Pass-through-Stubs (`def x(state): return state`) bereitstellen, die AG-2 ersetzt.

## Schnittstellen & Signaturen

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

## Umsetzungsschritte

- [ ] `agent/__init__.py` und `agent/nodes/__init__.py` anlegen (leere Pakete).
- [ ] `agent/state.py` mit `Intent` (StrEnum, 5 Werte) erstellen.
- [ ] `TutorState`-Dataclass mit Pflichtfeldern (`student_id`, `subject_key`, `skill_key`, `intent`) und optionalen Eingaben (`answer`, `item_ref`) anlegen.
- [ ] Ergebnisfelder ergänzen; `retrieved` mit `field(default_factory=list)`, alle übrigen mit `None`-Default.
- [ ] `agent/graph.py` mit `build_graph()` erstellen; fünf `add_node`, Entry-Point `route`.
- [ ] Kante `route → retrieve`; bedingte Verzweigung nach `retrieve` via `branch` (ANSWER → assess, sonst explain).
- [ ] Kanten `assess → update_model → END` und `explain → END`.
- [ ] `return g.compile()`.
- [ ] Sicherstellen, dass `build_graph()` gegen die in `pyproject.toml` gepinnte `langgraph>=0.2`-Version kompiliert; bei API-Abweichung Doc-Hinweis ergänzen, **keine** API erfinden.
- [ ] (Falls AG-2 noch nicht da) Node-Stubs `def x_node(state): return state` bereitstellen, damit der Import gelingt.

## Akzeptanzkriterien

- [ ] `TutorState` + `Intent` sind wie spezifiziert definiert (AG-1).
- [ ] `build_graph()` verdrahtet: route → retrieve → (assess → update_model | explain) → END.
- [ ] `build_graph()` kompiliert fehlerfrei und gibt ein invocierbares Graph-Objekt zurück.
- [ ] Der Bewertungspfad und der generative Pfad sind durch die bedingte Kante strukturell getrennt (P2).
- [ ] `agent/` bleibt eine flache, einzelne Implementierung — keine Plugin-Registry (P7).

## Tests / Verifikation

- [ ] Import-/Kompilier-Smoke: `uv run python -c "from its.agent.graph import build_graph; g = build_graph(); print(type(g))"` läuft ohne Fehler.
- [ ] `uv run python -c "from its.agent.state import TutorState, Intent; print(list(Intent))"` listet die fünf Intents.
- [ ] (Optional, mit Stubs) `uv run pytest tests/test_agent_graph_smoke.py -q` — Graph kompiliert; `branch` liefert für `Intent.ANSWER` "assess", sonst "explain".

## Abhängigkeiten

- **RET-1** (`retrieval/router.py`: `route`, `RouteDecision`, `Mode`) — der `route`-Node (AG-2) konsumiert dies; das State-Feld `route_reason` spiegelt `RouteDecision.reason`.
- **LM-2** (`learner_model/tracing.py`: `record_attempt`) — `update_model` (AG-2) schreibt darüber; `TutorState.mastery` nimmt das Ergebnis auf.
- **GR-1** (`grading/registry.py`/`grading/base.py`: `get_grader`, `Item`, `GradeResult`) — `assess` (AG-2) nutzt dies; `TutorState.grade` spiegelt `GradeResult`.
- **Nachgelagert:** AG-2 (füllt die Nodes), API-1/E9 (mountet den Graphen hinter `/student/turn`), TST-3/E12 (Integrationstest gegen `build_graph()`).

## Definition of Done

- [ ] Akzeptanzkriterien dieses Tasks erfüllt.
- [ ] Tests grün (Kompilier-/Smoke-Test); Safety-Tests nicht betroffen (kein DB-Schreibpfad in AG-1).
- [ ] Keine PII in externen LLM-Prompts — in AG-1 nicht betroffen (kein LLM-Call).
- [ ] `uv`-only, keine `pip`-Aufrufe.
- [ ] GitHub-Issue AG-1 geschlossen, E8-Epic-Checkliste aktualisiert.
