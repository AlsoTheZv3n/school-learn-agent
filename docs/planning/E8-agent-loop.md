# E8 — Agent-Loop (LangGraph) — Detailplanung

## 1. Scope & Zielbild

Dieses Epic baut das **pädagogische Modell** des ITS — den Agenten, der erklärt, abfragt und den nächsten Schritt wählt — als explizite, auditierbare LangGraph-State-Machine. Es sitzt im Milestone **M3 Learning Engine** und ist das integrierende Stück, das die bereits vorhandenen Bausteine zusammenführt: den Retrieval-Router (RET-1), den Tracing-/BKT-Schreibpfad (LM-2), die Grader-Registry (GR-1) und die FastAPI-Config (FND-4).

**Zielbild am Ende des Epics:**

- `agent/state.py` definiert das Zustandsschema `TutorState` plus das `Intent`-Enum.
- `agent/graph.py` kompiliert einen Graphen mit fünf Knoten und einer bedingten Verzweigung: `route → retrieve → conditional(assess → update_model | explain) → END`.
- Die fünf Knoten in `agent/nodes/` implementieren die Loop-Semantik: kuratierte Bewertung (P2), Modell-Update via `record_attempt` mit Konfidenz-Gate (P3/P6), generativer Erklärungspfad mit anonymisiertem Kontext (P4).
- Der LLM-Client (`llm/client.py`) scrubbt PII vor jedem externen Call und ist per Config zwischen lokal und Frontier umschaltbar; `llm/anonymize.py` und `llm/prompts/` sind vorhanden.
- Ein voller `ANSWER`-Turn läuft end-to-end: Frage → Antwort → Bewertung (Konfidenz 1.0) → Mastery-Update.

**Explizit NICHT in diesem Epic** (Abgrenzung): die HTTP-Endpoints (`api/student.py`, E9/API-1), das Frontend (E10/E11), der eigentliche Integrationstest `tests/test_agent_turn.py` (formal TST-3 in E12 — wir liefern hier aber bereits einen lauffähigen Smoke-Pfad), die Grader-Implementierungen selbst (GR-2/GR-3) sowie die in `docs/07` referenzierte, aber nirgends spezifizierte Funktion `content/items.py::load_item` (siehe offene Fragen).

## 2. Task-Reihenfolge & Abhängigkeiten

```
Vorbedingungen (andere Epics):
  RET-1 (router.route/RouteDecision/Mode) ─┐
  LM-2  (record_attempt -> learner_state)  ─┼─► AG-1
  GR-1  (get_grader/Item/GradeResult)      ─┘
  FND-4 (settings.llm_backend, config)     ───► AG-3

Innerhalb E8:
  AG-1 ──► AG-2
  AG-3 ──► AG-2   (AG-2.explain/AG-2.assess hängen an llm/client + (indirekt) grader)
  AG-1, AG-2, AG-3 ──► (nachgelagert) API-1 (E9), TST-3 (E12)
```

Empfohlene Implementierungsreihenfolge: **AG-3** (LLM-Client/Anonymisierung, da `safety-critical` und unabhängig von AG-1) und **AG-1** (State + Graphgerüst) können parallel starten; **AG-2** schliesst ab, weil die Nodes sowohl das State-Schema (AG-1) als auch den LLM-Client (AG-3) brauchen.

> Hinweis: AG-2 ist im Issue-Inventar nur formal von AG-1 abhängig. Faktisch braucht der `explain`-Node `llm/client.complete` aus AG-3 — daher AG-3 vor (oder mit) AG-2 fertigstellen.

## 3. Feinere Sub-Task-Zerlegung (über die Issues hinaus)

**AG-1**
- 1a. `Intent`-StrEnum (ANSWER/EXPLAIN/HINT/WHY/NEXT).
- 1b. `TutorState`-Dataclass mit Input-Feldern und von Nodes befüllten Ergebnisfeldern (`field(default_factory=list)` für `retrieved`).
- 1c. `build_graph()` mit `StateGraph(TutorState)`, fünf `add_node`, Entry-Point `route`, Kante `route→retrieve`, bedingter Verzweigung nach `retrieve`, Kanten `assess→update_model→END` und `explain→END`, Rückgabe `g.compile()`.
- 1d. Klärung: liefern LangGraph-Nodes mutierte Dataclass-Instanzen oder Dict-Patches? (siehe Designentscheidung 4.1).
- 1e. Mini-Smoke: `build_graph()` kompiliert ohne Fehler (Import-/Verdrahtungstest, keine DB).

**AG-2**
- 2a. `route_node`: `has_scope = bool(student_id)`; bei ANSWER/NEXT `route("student progress", …)`, sonst `route(skill_key, …)`; setzt `route_reason = f"{decision.mode}:{decision.reason}"`.
- 2b. `retrieve_node`: ruft je nach `route` `semantic`/`individual`/`population`; legt Ergebnis in `state.retrieved`. (Session-/Scope-Übergabe klären, siehe 4.3.)
- 2c. `assess_node`: Guard auf `answer`/`item_ref`; `load_item(item_ref)`; `get_grader(subject_key)`; `grader.grade(...)`; schreibt `state.grade = {correct, feedback, confidence}`.
- 2d. `update_model_node`: Guard auf `state.grade`; **nur** bei `confidence >= 0.9` `Attempt` anlegen + `record_attempt` aufrufen + `state.mastery` setzen + `commit`.
- 2e. Hilfsfunktion `_skill_id(skill_key) -> uuid` (Auflösung Skill-Key → Skill-UUID; siehe offene Frage).
- 2f. `explain_node`: baut Prompt nur aus `skill_key` + `intent` (kein Name, P4); ruft `complete(system=EXPLAIN_SYSTEM, user=…)`.
- 2g. `branch(state)`-Funktion für die bedingte Kante (ANSWER→assess, sonst explain).

**AG-3**
- 3a. `anonymize.py::scrub(text)` mit den drei Regex-Pattern (Name/Datum/E-Mail).
- 3b. `client.py::complete(system, user)`: `user = scrub(user)` zuerst; Backend-Switch über `settings.llm_backend`.
- 3c. `_complete_frontier`/`_complete_local`-Implementierungen (oder klar markierte Stubs; konkrete SDK-Wahl ist offen).
- 3d. `prompts/__init__.py` mit `EXPLAIN_SYSTEM` (Ton: altersgerecht, knapp, ermutigend; keine endgültigen Bewertungen).
- 3e. Defense-in-depth-Doku: scrub ist die zweite Verteidigungslinie; primär werden nur IDs/Keys übergeben.

## 4. Zentrale Designentscheidungen mit Begründung

**4.1 State als Dataclass, mutierende Nodes.** `docs/07` definiert `TutorState` als `@dataclass` und alle Nodes als `def node(state) -> state` (mutieren und zurückgeben). Wir folgen exakt diesem Muster. Begründung: Das Quelldokument ist normativ; der explizite, lesbare State macht das Routing auditierbar (P3/P6). Falls die genutzte LangGraph-Version Dict-State erwartet, wird das als Adaptierung dokumentiert, nicht als API erfunden (siehe offene Fragen).

**4.2 Kuratierte Bewertung strikt getrennt vom generativen Pfad (P2).** Der Graph verzweigt nach `retrieve`: `ANSWER` geht durch `assess→update_model`, alles andere (EXPLAIN/HINT/WHY/NEXT) durch `explain`. Damit kann ein LLM strukturell nie eine „korrekt/falsch"-Entscheidung beeinflussen — diese kommt allein aus `grader.grade()` gegen den kuratierten `answer_key`.

**4.3 Konfidenz-Gate beim Zementieren (P6).** `update_model_node` schreibt nur dann in `learner_state`, wenn `grade["confidence"] >= 0.9`. Der Math-Grader liefert deterministisch `confidence=1.0` (zementiert), der History-Grader liefert bewusst `< 1.0` (geht in Lehrer-Review statt automatischem Schreiben). Der Schwellwert 0.9 stammt aus dem Doc-Beispielcode.

**4.4 Anonymisierung als zweite Verteidigungslinie (P4).** Primär werden dem LLM ohnehin nur Skill-Keys/IDs übergeben; `scrub` ist defense-in-depth für den Fall, dass freier Text durchsickert. `scrub` läuft in `client.complete()` **vor** jeder Backend-Verzweigung, sodass kein Pfad daran vorbeiführt.

**4.5 Eine Implementierung, nur ein Adapterpunkt (P7).** Der Agent-Loop, der Router-Aufruf und der Tracing-Aufruf sind flache, einzelne Implementierungen. Der einzige Strategy-Punkt ist `get_grader(subject_key)` — dieser gehört zu GR-1 und wird vom Agenten nur konsumiert, nicht erweitert.

**4.6 Session-Handling.** Das Doc zeigt `with SessionLocal() as s:` mit dem ausdrücklichen Kommentar „in der Praxis: die request-scoped Session injizieren". Wir bauen `update_model_node` so, dass es innerhalb des RLS-gescopten Session-Kontexts (`scoped_session`, DB-3) läuft. Wie die Session konkret in den Node gelangt (Closure/Factory/State-Feld) ist eine offene Entscheidung (siehe 6).

## 5. Risiken & Gegenmassnahmen

- **R1 — `load_item` ist nirgends spezifiziert.** `assess_node` importiert `from its.content.items import load_item`, aber weder Datei noch Signatur existieren im Plan. Gegenmassnahme: minimalen, klar dokumentierten Loader definieren (Signatur + Quelle des `answer_key`) oder als blockierende Abhängigkeit eskalieren (offene Frage 1).
- **R2 — Session-Lebenszyklus bricht RLS.** Wenn `update_model_node` eine eigene, ungescopte `SessionLocal()` öffnet, umgeht es den RLS-Kontext. Gegenmassnahme: Node innerhalb `scoped_session(principal)` betreiben; Test, dass ohne `student_id` nichts geschrieben wird.
- **R3 — PII-Leck über freien Text.** Trotz P4 könnte ein zukünftiger Node Freitext (z. B. `raw_answer`) an den LLM geben. Gegenmassnahme: `scrub` ausnahmslos in `complete()`; Unit-Test `test_anonymize.py` (Name/Datum/E-Mail) sowie ein Test, dass `explain_node` keinen Namen in den Prompt schreibt.
- **R4 — LangGraph-API-Drift.** Die im Doc gezeigte API (`StateGraph`, `add_conditional_edges`, `compile`, `invoke`) kann je nach `langgraph>=0.2`-Minor variieren. Gegenmassnahme: gegen die in `pyproject.toml` gepinnte Version implementieren; keine APIs erfinden; bei Abweichung Doc-Hinweis im Issue.
- **R5 — Konfidenz-Gate falsch verdrahtet.** Ein Bug, der auch bei niedriger Konfidenz schreibt, verletzt P6 direkt. Gegenmassnahme: dedizierter Test mit `confidence=0.5` → kein `learner_state`-Write, `state.mastery is None`.
- **R6 — `skill_key → skill_id`-Auflösung.** `update_model_node` braucht eine UUID, hat aber nur den Key. Gegenmassnahme: `_skill_id`-Helper mit DB-Lookup über `skills.key` definieren (offene Frage 4).
- **R7 — Frontier-Backend leakt Daten ausserhalb CH/EU (P8).** Wenn `llm_backend=frontier` einen Nicht-EU-Endpoint nutzt, verletzt das die Datenresidenz. Gegenmassnahme: in Produktion `local` (Qwen2.5) o. CH/EU-Region; im Code/Doku den Residenz-Constraint vermerken.

## 6. Offene Fragen / zu treffende Entscheidungen

1. **`content/items.py::load_item` — Signatur und Datenquelle.** Nirgends im Plan spezifiziert; `assess_node` hängt hart davon ab. Wo liegt der kuratierte `answer_key` (DB-Tabelle? Vault-Datei? Frontmatter)? Vorschlag: minimaler DB-/Datei-Loader, der ein `Item(skill_key, prompt, answer_key, rubric)` liefert.
2. **State-Repräsentation für LangGraph.** Erwartet die gepinnte `langgraph`-Version Dataclass-State (wie im Doc) oder einen TypedDict/Dict-Patch? Das beeinflusst, ob Nodes mutieren oder Patches zurückgeben.
3. **Session-Injektion in `update_model_node`.** Wie kommt die request-scoped, RLS-gescopte Session in den Node — über Closure beim `build_graph()`, über ein State-Feld, oder über eine ContextVar?
4. **`skill_key → skill_id`-Auflösung.** Genaue Quelle/Helper für die UUID (Lookup in `skills` per `key`, ggf. mit `subject_id`-Scope).
5. **LLM-Backend-Konkretisierung (AG-3).** Welches lokale Modell (Qwen2.5-Variante/Grösse) und welches Frontier-SDK/welcher Endpoint? Welcher Endpoint erfüllt P8 (CH/EU)?
6. **Konfidenz-Schwelle 0.9.** Fix oder konfigurierbar (`settings`)? Pro Fach unterschiedlich (Math 1.0 vs. History < 1.0)?
7. **`retrieve_node`-Detailverhalten.** Welche konkreten Argumente (Session, Embedding, class_id) bekommen `semantic`/`individual`/`population`? Das Doc beschreibt nur „je nach route".

## 7. Test-/Verifikationsstrategie für das Epic

- **Unit (keine DB):**
  - `tests/test_anonymize.py` — `scrub` ersetzt Name/Datum/E-Mail (P4).
  - Graph-Kompilier-Smoke: `build_graph()` importiert/kompiliert ohne Fehler.
  - `route_node`-Logik: ANSWER/NEXT → INDIVIDUAL-Tendenz, sonst SEMANTIC; `route_reason` gesetzt.
  - Konfidenz-Gate isoliert: `update_model_node` mit Fake-`grade` (`confidence=0.5`) schreibt nicht.
- **Integration (Test-DB, transaktional, RLS aktiv — `conftest.py`/`db_factory` aus E12):**
  - `tests/test_agent_turn.py` (TST-3): voller `ANSWER`-Turn → `result.grade["confidence"] == 1.0` (kuratiert, P2) und `result.mastery is not None` (Modell aktualisiert, P3).
  - Gegenprobe Konfidenz < 0.9 → `learner_state` unverändert (P6).
- **Backend-Constraint:** Tests gegen echtes Postgres mit RLS (kein SQLite), damit der Schreibpfad in `update_model` die Isolation respektiert.
- **Befehle:** `uv run pytest tests/test_anonymize.py -q`, `uv run pytest tests/test_agent_turn.py -q`, gesamte Suite `uv run pytest -q`. Kein `pip` (P9).
