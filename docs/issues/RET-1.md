## Ziel

Eine reine Routing-Funktion `route(question, *, has_student_scope)` entscheidet pro Anfrage den **Modus** (semantic / individual / population) und ob auf eine **strukturierte Live-Query** eskaliert werden muss. Die Entscheidung wird als `RouteDecision` mit menschenlesbarer Begruendung zurueckgegeben und geloggt, sodass das Routing nachvollziehbar (auditierbar) ist.

## Kontext & Prinzipien

- **P6 (Mensch im Loop / auditierbares Routing):** Die `reason` in `RouteDecision` ist nicht kosmetisch — sie macht jede Routing-Entscheidung im Log nachvollziehbar. Auch wenn der Router spaeter durch einen Klassifikator ersetzt wird, bleibt das explizite `reason`-Feld erhalten.
- **P1 (Safety in der DB):** Der Router faellt eine *Routing*-, keine *Autorisierungs*-Entscheidung. Selbst eine falsche Modus-Wahl darf keine Daten leaken — die Isolation liegt in RLS (RET-3) und Min-Cohort (RET-4), nicht hier. Konkret: bei `has_student_scope=False` darf der Router **nie** INDIVIDUAL zurueckgeben (Fallback auf SEMANTIC), damit kein ungescopter Individual-Pfad entsteht.
- **P7 (genau eine Plugin-Naht):** Der Router ist **eine** Implementierung, kein Strategy/Registry-Muster. Er liegt als flaches Modul in `retrieval/`.
- **P9 (`uv`-only):** Keine neue Dependency noetig; falls doch, `uv add`, niemals `pip`.

## Zu erstellende/aendernde Dateien

- `apps/api/src/its/retrieval/router.py` (neu) — Kernimplementierung.
- `apps/api/src/its/retrieval/__init__.py` (neu, falls noch nicht vorhanden) — Paket-Init.
- `tests/test_router.py` (neu) — Unit-Tests (keine DB noetig).

## Schnittstellen & Signaturen

Referenz aus `docs/05-retrieval.md`, Abschnitt 1 — exakt zu reproduzieren:

```python
from dataclasses import dataclass
from enum import StrEnum

class Mode(StrEnum):
    SEMANTIC = "semantic"
    INDIVIDUAL = "individual"
    POPULATION = "population"

@dataclass(frozen=True)
class RouteDecision:
    mode: Mode
    escalate_to_query: bool   # True = strukturierte Live-Query statt nur Prosa
    reason: str               # Begruendung (Logging/Audit)

def route(question: str, *, has_student_scope: bool) -> RouteDecision:
    """Heuristik/Klassifikation. Start: regelbasiert; spaeter Klassifikator.
    - Aggregat-/Vergleichsbegriffe ("Klasse", "Durchschnitt", "alle") -> POPULATION
    - Personenbezug auf den Lernenden ("mein Stand", "wo stehe ich") -> INDIVIDUAL
    - sonst erklaerend -> SEMANTIC
    Eskalation, wenn frische/praezise Zahlen verlangt werden."""
    ...
```

Konsument (aus `docs/07-agent.md`, `agent/nodes/route.py`) — zeigt die erwartete Nutzung:

```python
from its.retrieval.router import route, Mode

def route_node(state):
    has_scope = bool(state.student_id)
    decision = route(state.skill_key, has_student_scope=has_scope)
    state.route_reason = f"{decision.mode}:{decision.reason}"
    return state
```

## Umsetzungsschritte

- [ ] `Mode`-StrEnum und `RouteDecision`-Dataclass (`frozen=True`) exakt wie oben anlegen.
- [ ] Schluesselwort-Konstanten (Deutsch) definieren: `POPULATION_TERMS` (z. B. "klasse", "durchschnitt", "alle", "kohorte", "verteilung"), `INDIVIDUAL_TERMS` (z. B. "mein stand", "wo stehe ich", "mein fortschritt", "meine"), `ESCALATION_TERMS` (z. B. "genau", "aktuell", "zahl", "durchschnitt", "wie viele").
- [ ] `route()` regelbasiert implementieren, als geordnete Praedikat-Liste (erste Regel gewinnt): (1) Aggregatbegriff → POPULATION, (2) Personenbezug **und** `has_student_scope` → INDIVIDUAL, (3) sonst → SEMANTIC.
- [ ] **Fail-safe-Regel:** Wuerde Regel (2) ohne `has_student_scope` greifen, auf SEMANTIC zurueckfallen und das in `reason` vermerken (kein ungescopter Individual-Pfad).
- [ ] `escalate_to_query` setzen, wenn ein Eskalations-Term vorkommt (frische/praezise Zahlen verlangt). POPULATION impliziert i. d. R. Eskalation (echte Aggregat-Query).
- [ ] `reason` mit dem ausschlaggebenden Term/Pfad fuellen (z. B. `"population: matched 'durchschnitt'"`).
- [ ] Logging: `logging.getLogger("its.retrieval.router")`, pro Aufruf `logger.info("route decision", extra={"mode": ..., "escalate": ..., "reason": ...})`.
- [ ] Eingabe normalisieren (lowercase, trim) vor dem Matching.
- [ ] `ruff`-clean (line-length 100, py312).

## Akzeptanzkriterien

- [ ] `route()` liefert immer ein `RouteDecision` mit gesetztem `mode`, `escalate_to_query` und nicht-leerem `reason`.
- [ ] Aggregat-/Vergleichsbegriffe → `Mode.POPULATION`.
- [ ] Personenbezug **mit** `has_student_scope=True` → `Mode.INDIVIDUAL`.
- [ ] Personenbezug **ohne** Scope → **nicht** INDIVIDUAL (Fallback SEMANTIC), nachvollziehbar in `reason`.
- [ ] Sonstige/erklaerende Fragen → `Mode.SEMANTIC`.
- [ ] Eskalations-Trigger setzt `escalate_to_query=True`.
- [ ] Jede Entscheidung wird geloggt (auditierbar, P6).

## Tests / Verifikation

```bash
cd apps/api
uv run pytest ../../tests/test_router.py -q
```

Erwartete Tests/Ergebnisse:
- `route("Wie ist der Durchschnitt der Klasse?", has_student_scope=True).mode == Mode.POPULATION`
- `route("Wo stehe ich gerade?", has_student_scope=True).mode == Mode.INDIVIDUAL`
- `route("Wo stehe ich gerade?", has_student_scope=False).mode == Mode.SEMANTIC` (Fail-safe)
- `route("Was bedeutet quadratische Ergaenzung?", has_student_scope=True).mode == Mode.SEMANTIC`
- `route("Wie viele genau haben das gemeistert?", ...).escalate_to_query is True`
- Jede `RouteDecision.reason` ist nicht leer.

## Abhaengigkeiten

- **SAF-2** (`require_student_scope`): liefert das Konzept des Schueler-Scopes; der Router muss `has_student_scope` respektieren, damit kein ungescopter Individual-Pfad entsteht.
- **SAF-3** (`enforce_min_cohort`): begruendet, warum der Router POPULATION gefahrlos waehlen darf — die De-Anonymisierung wird nachgelagert verhindert.
- **Nachgelagert:** AG-2 (`agent/nodes/route.py`, `docs/07`) ruft `route()` auf; RET-2/3/4 werden je nach Modus von `agent/nodes/retrieve.py` aufgerufen.

> Hinweis: zu entscheiden — die genauen deutschen Schluesselwort-Listen sind im Doc nur beispielhaft; die finale Term-Liste sollte mit den geplanten Frage-Templates des Frontends (docs/09) abgeglichen werden.

## Definition of Done

- [ ] Akzeptanzkriterien (oben) erfuellt.
- [ ] `tests/test_router.py` gruen.
- [ ] Kein LLM betroffen (reine Funktion) → keine PII-Pruefung noetig.
- [ ] `uv`-only, keine `pip`-Aufrufe.
- [ ] GitHub-Issue RET-1 geschlossen, E4-Checkliste aktualisiert.
