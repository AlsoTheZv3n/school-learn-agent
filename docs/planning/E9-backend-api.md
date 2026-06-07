# E9 — Backend-API (Student + Teacher) — Detailplanung

> Quelldokument: `docs/08-backend-api.md`. Milestone: **M4 — API & Frontend**.
> Querbezüge: `docs/00-architecture.md` (Prinzipien P1-P9, Layout §6, DoD §8), `docs/02-foundations.md` (FND-4: `config.py`, `main.py`, `auth/deps.py`), `docs/03-database.md` (DB-3: `scoped_session`, Modelle), `docs/04-safety.md` (SAF-2 `scoping.py`, SAF-3 `cohort.py`, RLS-Policies), `docs/05-retrieval.md` (RET-3 `individual.py`, RET-4 `population.py`), `docs/07-agent.md` (AG-1 `state.py`/`graph.py`), `docs/10-testing.md` (Fixtures `db_factory`, HTTP-Smoke).

---

## 1. Scope & Zielbild

E9 baut die **HTTP-Naht** des ITS: zwei FastAPI-Router (`/student`, `/teacher`) plus ein gemeinsames Pydantic-Schema- und Fehlermodell. Die API selbst enthält **keine** Geschäftslogik — sie ist eine dünne, validierende Schicht, die:

1. das authentifizierte `Principal` (Rolle + `student_id`/`user_id`) entgegennimmt,
2. **jeden** personenbezogenen Zugriff in eine `scoped_session(principal)` einwickelt (setzt PG-Rolle + Session-Variable → speist RLS, P1),
3. den LangGraph-Agent-Loop (`/student/turn`) bzw. die Retrieval-Funktionen (`individual.py`, `population.py`) aufruft,
4. Safety-Ausnahmen (`ScopeError`, `CohortTooSmall`) zentral auf neutrale `403`/`404`-Antworten mappt (keine Detail-Leaks),
5. nach aussen die **schonende** Schülersicht (nur `mastery`) und nach innen die **vollständige** Lehrersicht (inkl. `uncertainty`, Open Learner Model, P5) trennt.

Zielzustand am Epic-Ende:
- `POST /student/turn`, `GET /student/mastery` funktionieren end-to-end gegen die Test-DB.
- `GET /teacher/student/{id}/mastery`, `GET /teacher/class/{id}/skill/{id}/distribution`, `POST /teacher/student/{id}/note` funktionieren, RLS- und Min-Cohort-gefiltert.
- Ein zentraler Exception-Handler ist in `main.py` registriert; beide Router sind gemountet.
- HTTP-Tests beweisen die drei Safety-Eigenschaften: Schüler sieht nur sich; Lehrer nur die eigene Klasse; kleine Kohorte → `403`.

**Nicht im Scope** (bewusst): echtes JWT-Decoding (das ist FND-5, hier nur Stub-Konsum), das Frontend (E10/E11), die Implementierung von `build_graph`/`mastery_overview`/`skill_mastery_distribution` (das sind AG-1/RET-3/RET-4), `load_item`/`content/items.py` (offen, siehe §6).

---

## 2. Task-Reihenfolge & Abhängigkeiten

Innerhalb des Epics ist API-3 die Basis (Schemas werden von beiden Routern importiert), danach API-1, danach API-2:

```
FND-4 ─────────────► API-3 (Schemas + Fehlermodell)
                        │
AG-1, SAF-2 ──────────► API-1 (Student-Endpoints) ─┐
                        │                            │
API-1, RET-4 ─────────► API-2 (Teacher-Endpoints) ◄─┘
```

Externe Voraussetzungen (müssen vor Code-Start grün sein):
- **FND-4**: `its.config.settings`, `its.main.create_app`, `its.auth.deps.Principal`/`current_principal`.
- **AG-1**: `its.agent.state.TutorState`/`Intent`, `its.agent.graph.build_graph`.
- **SAF-2**: `its.safety.scoping.ScopeError`/`require_student_scope`, `its.db.session.scoped_session` (DB-3), RLS-Policies live in der DB (SAF-1).
- **RET-4**: `its.retrieval.population.skill_mastery_distribution` + `its.safety.cohort.enforce_min_cohort`/`CohortTooSmall` (SAF-3).
- Implizit für `/student/mastery`: **RET-3** `its.retrieval.individual.mastery_overview`.

Nachgelagert warten auf E9:
- **FE-S2** (Schüler-Session-Screen) auf **API-1**.
- **FE-T1/FE-T2/FE-T3** (Lehrer-Dashboard, Open Learner Model, Interventionen) auf **API-2**.
- **TST-4** (E2E-/HTTP-Smoke) auf **API-2**.

---

## 3. Feinere Sub-Task-Zerlegung (über die drei Issues hinaus)

**API-3 (Schemas + Fehlermodell)**
- S3.1 `schemas.py` mit allen sechs Modellen (`TurnRequest`, `GradeOut`, `TurnResponse`, `SkillMastery`, `CohortStat`) anlegen; `Intent` aus `its.agent.state` importieren.
- S3.2 Exception-Handler-Funktionen definieren (`safety_exception_handler`, `lookup_exception_handler`).
- S3.3 Eine `register_error_handlers(app)`-Funktion, die in `main.py` aufgerufen wird (entkoppelt von `main.py`, damit Tests sie isoliert prüfen können).
- S3.4 Neutrale Fehlermeldungen festlegen (z. B. `{"detail": "forbidden"}`), keine Exception-Texte durchreichen.

**API-1 (Student-Endpoints)**
- S1.1 `student.py` mit `APIRouter(prefix="/student")` + Modul-globaler `_graph = build_graph()`.
- S1.2 `POST /student/turn`: `TurnRequest` → `TutorState` → `with scoped_session(principal): _graph.invoke(state)` → `TurnResponse`.
- S1.3 Defensive Behandlung von `result` (LangGraph kann ein dict statt Dataclass zurückgeben — siehe Risiken/offene Fragen).
- S1.4 `GET /student/mastery`: `mastery_overview(s, principal)` → Liste `SkillMastery`, UI zeigt nur `mastery`.
- S1.5 Import von `GradeOut`/`SkillMastery` in `student.py` ergänzen (im Doc-Auszug fehlt der `GradeOut`-Import → korrigieren).

**API-2 (Teacher-Endpoints)**
- S2.1 `teacher.py` mit `APIRouter(prefix="/teacher")`.
- S2.2 `GET /teacher/student/{id}/mastery`: RLS-gefilterte Roh-Query inkl. `uncertainty`.
- S2.3 `GET /teacher/class/{id}/skill/{id}/distribution`: über `skill_mastery_distribution` (→ `enforce_min_cohort`).
- S2.4 `POST /teacher/student/{id}/note`: Insert in `teacher_notes` (Notiz + optionaler `override_mastery`); `body`/`skill_id`/`override_mastery` als Request-Body-Schema statt loser Query-Params (Designentscheidung, §4).
- S2.5 `from sqlalchemy import text` ergänzen (im Doc-Auszug für `teacher.py` fehlt der `text`-Import → korrigieren).

**Querschnitt**
- X.1 `main.py` erweitern: beide Router mounten + `register_error_handlers(app)`.
- X.2 HTTP-Tests: `tests/test_api_student.py`, `tests/test_api_teacher.py` mit `httpx`/`TestClient` und `current_principal`-Override.

---

## 4. Zentrale Designentscheidungen mit Begründung

1. **Schemas in eigenem Modul (`api/schemas.py`), Fehler-Handler in `register_error_handlers`.** Beide Router importieren die Schemas; ein zentrales Fehlermodell garantiert *eine* Mapping-Stelle (P1: Safety als Eigenschaft, nicht verstreute `if`-Checks).
2. **Keine Geschäftslogik in der API.** `turn` ruft nur `_graph.invoke`; `mastery` ruft nur `mastery_overview`; `distribution` ruft nur `skill_mastery_distribution`. So bleibt die Plugin-Asymmetrie aus P7 erhalten (genau eine Naht = grading; API ist *eine* Implementierung, kein Strategy-Punkt).
3. **`scoped_session(principal)` umschliesst jeden personenbezogenen Zugriff.** Das ist die Brücke zu RLS (DB-3 + SAF-1). Selbst eine fehlerhafte Query liefert keine Fremdzeilen — Doppel-Absicherung mit `require_student_scope` (P1).
4. **Schonende vs. vollständige Sicht über zwei verschiedene Endpoints, nicht über ein Flag.** `/student/mastery` liefert zwar das volle `SkillMastery`-Objekt (inkl. `uncertainty`), aber die UI (E10) zeigt nur `mastery`; die *Roh*-Lehrersicht ist `/teacher/...`. P5: die Unsicherheit gehört der Lehrperson. > Hinweis: zu entscheiden — ob der Schüler-Endpoint `uncertainty` gar nicht erst serialisieren soll (eigenes `StudentSkillMastery`-Schema) statt sich auf UI-Disziplin zu verlassen. Empfehlung: eigenes schlankes Schema (siehe offene Fragen).
5. **Safety-Exceptions → `403` neutral, `LookupError` → `404`, Validierung → `422` (FastAPI-Default).** Neutrale Meldung verhindert, dass die Antwort selbst (z. B. „Kohorte n=3") zur De-Anonymisierungs-Quelle wird (Aggregat-Leak aus docs/04 §1).
6. **`POST /note` nimmt einen Pydantic-Body statt loser Query-Parameter.** Der Doc-Auszug zeigt `body: str` als Query-Param; das ist für längeren Notiztext unpraktisch und sendet PII in der URL (Logging-Leak). Designentscheidung: ein `NoteIn`-Schema. > Hinweis: zu entscheiden — Schema-Name/Felder; Default-Empfehlung in offenen Fragen.
7. **`_graph = build_graph()` als Modul-Singleton.** Der kompilierte LangGraph ist zustandslos bzgl. Request-Daten (der State wird pro `invoke` übergeben); ein einmaliger Build spart Kosten pro Request. > Hinweis: zu entscheiden — wie die request-scoped DB-Session in die Agent-Nodes injiziert wird (docs/07 nutzt im `update_model`-Node ein eigenes `SessionLocal()`, der API-Code öffnet aber bereits `scoped_session`).

---

## 5. Risiken & Gegenmassnahmen

| Risiko | Gegenmassnahme |
|---|---|
| Doppelte/uneinheitliche DB-Session: `/student/turn` öffnet `scoped_session`, aber der `update_model`-Node (docs/07) öffnet ein eigenes `SessionLocal()` ohne Rollen-/`student_id`-Kontext → schreibt evtl. RLS-ungeschützt. | Die request-scoped Session in den Graph-State/-Kontext injizieren; in der Issue als expliziter Schritt + offene Frage geführt. Nicht selbst „erfinden", sondern mit AG-Owner klären. |
| API leakt Detailtexte aus Safety-Exceptions (z. B. Kohortengrösse) → De-Anonymisierung. | Zentraler Handler gibt neutrale Meldung; Exception-Text wird nur geloggt, nicht serialisiert. Test prüft, dass Response-Body keine `n=`-Info enthält. |
| `current_principal` ist noch ein Stub (FND-5) und wirft `NotImplementedError` → Endpoints nicht testbar ohne echtes JWT. | In Tests `app.dependency_overrides[current_principal]` setzen; in Doku klar als Vorbedingung markieren. |
| `result: TutorState = _graph.invoke(state)` — LangGraph gibt häufig ein `dict` (State-Schema-Serialisierung) zurück, nicht die Dataclass. `result.grade` würde dann fehlschlagen. | Defensiv auf dict-Zugriff vorbereiten (`result.get(...)` vs. Attribut), in der Issue als Schritt + offene Frage; nicht raten. |
| `POST /note` schreibt PII (Freitext über Minderjährige) in der URL bei Query-Param-Variante → landet in Server-/Proxy-Logs. | Body-Schema statt Query-Param (Designentscheidung 6). |
| RLS nicht in der Test-DB aktiv → HTTP-Tests bestehen falsch-positiv. | Tests laufen gegen echtes Postgres mit angewandtem `rls.sql` (Fixtures `engine`/`db_factory` aus docs/10); kein SQLite. |
| `mastery_overview` liefert dict-Keys, die nicht 1:1 zu `SkillMastery`-Feldern passen (`skill_id` ist in RET-3 ein UUID-Objekt, das Schema erwartet `str`). | `SkillMastery(**r)` setzt passende Keys/Typen voraus; in der Issue als Verifikationsschritt; ggf. `::text`-Cast wie in `teacher.py` (dort bereits `ls.skill_id::text`). |

---

## 6. Offene Fragen / zu treffende Entscheidungen

1. **`load_item` / `content/items.py`** (referenziert in docs/07 `assess_node`) ist nirgends spezifiziert. `POST /student/turn` mit `intent=answer` triggert `assess` → `load_item(item_ref)`. Ohne diese Funktion schlägt ein ANSWER-Turn fehl. Muss vor dem API-Integrationstest geklärt sein (gehört formal zu AG-2/Content, blockt aber API-1-Tests).
2. **DB-Session-Injektion in die Agent-Nodes**: docs/07 öffnet im `update_model`-Node ein eigenes `SessionLocal()` „in der Praxis: die request-scoped Session injizieren". Wie genau (LangGraph-Config/`configurable`, contextvar, State-Feld)? Betrifft P1 direkt.
3. **Rückgabetyp von `_graph.invoke`** (Dataclass vs. dict). Bestimmt, ob `result.grade` oder `result["grade"]` korrekt ist.
4. **Schonende Schülersicht**: eigenes `StudentSkillMastery`-Schema (ohne `uncertainty`) oder UI-Disziplin? Empfehlung: eigenes Schema (Defense-in-depth, P5).
5. **`POST /note`-Body-Schema** (Felder/Validierung von `override_mastery`-Range 0..1).
6. **Auth/Token-Herkunft fürs Frontend** (E10/E11): woher kommt das JWT, welche Claims mappen auf `student_id`/`user_id`/`role`? Betrifft `current_principal` (FND-5), aber die API definiert den Vertrag.
7. **`student_id` im Teacher-Pfad**: Path-Param ist `str`; muss als UUID gegen die DB gebunden werden — Validierung/Cast festlegen (Pydantic `UUID` im Pfad?).

---

## 7. Test-/Verifikationsstrategie für das Epic

- **Fixtures** aus docs/10 nutzen: `engine` (Alembic + `rls.sql` gegen Test-Postgres), `db_factory` (Rollen-Spiegel von `scoped_session`), `two_students`. Plus eine Seed-Fixture mit Klasse/Enrollment/Lehrer für die Teacher-Tests.
- **Auth in Tests**: `app.dependency_overrides[current_principal]` mit einem festen Schüler- bzw. Lehrer-`Principal`.
- **API-3**: Unit-Test, dass `ScopeError`/`CohortTooSmall` → `403` (neutraler Body, kein `n=`), `LookupError` → `404`, fehlerhafter Request-Body → `422`.
- **API-1**: HTTP-Test `GET /student/mastery` als Schüler A liefert nur eigene Skills; als Schüler B andere. `POST /student/turn` (EXPLAIN-Intent, der ohne `load_item` auskommt) liefert `200` mit `explanation`. ANSWER-Turn erst nach Klärung von offener Frage 1.
- **API-2**: Lehrer sieht `student/{id}/mastery` **nur** für Schüler der eigenen Klasse (Fremdschüler → leere Liste durch RLS, nicht `403`); `distribution` einer kleinen Kohorte (`n<k`) → `403`, grosser Kohorte → `200` mit `n`/`avg_mastery`; `POST /note` → `200` und Zeile in `teacher_notes` vorhanden.
- **HTTP-Smoke** (verzahnt mit TST-4): Schüler-Turn → `/student/mastery` → Lehrer `/teacher/student/{id}/mastery` (sieht zusätzlich `uncertainty`).
- **Befehle**: `uv run pytest tests/test_api_student.py tests/test_api_teacher.py -q` (gegen laufende Docker-DB); plus manueller `curl` auf `/health` und die Endpoints (siehe Task-Bodies).
- **CI**: Diese Tests laufen in der vollen Suite (`uv run pytest -q`); der vorgelagerte Safety-Schritt (`test_rls.py`, `test_cohort_threshold.py`) bleibt blockierend.

