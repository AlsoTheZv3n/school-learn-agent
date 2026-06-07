# E12 — Testing & CI — Detailplanung

> Quelle: `docs/10-testing.md` (Pyramide, Fixtures, CI-Gate), ergänzend `docs/04-safety.md` (§5 Safety-Tests, die hier mit den Fixtures laufen), `docs/00-architecture.md` (Prinzipien P1–P9, Repository-Layout §6, projektweite DoD §8). Milestone: **M6 Hardening**. Issues: **TST-1 … TST-4**.

## 1. Scope & Zielbild

E12 liefert die **Teststrategie als Querschnitt** über die gesamte Plattform. Es geht nicht darum, einzelne Features zu bauen, sondern die Eigenschaften, die diese Features versprechen, **maschinell und CI-blockierend** abzusichern. Zwei Dinge stehen im Zentrum:

1. **Safety-Eigenschaften absichern (nicht verhandelbar, P1).** Die eigentlichen Safety-Tests (`tests/test_rls.py`, `tests/test_cohort_threshold.py`) sind in `docs/04 §5` inhaltlich spezifiziert und gehören organisatorisch zu E3/SAF-4. E12 liefert die **Fixtures**, auf denen sie laufen (`conftest.py` mit transaktionaler Test-DB und `DBFactory`), und verdrahtet sie als **vorgelagerten, blockierenden CI-Schritt**.
2. **Kernlogik abdecken** entlang der Pyramide:

| Ebene | Was | Gegen was | Issue |
|---|---|---|---|
| **Safety** (kritisch) | RLS-Isolation, Min-Cohort | echtes Postgres mit RLS | (SAF-4, läuft auf TST-1-Fixtures) |
| **Unit** | BKT, Grader, Parser, Anonymizer | reine Funktionen, keine DB | TST-2 |
| **Integration** | Agent-Loop (ein voller `ANSWER`-Turn), Tracing-Schreibpfad | Test-DB | TST-3 |
| **E2E-Smoke** | Login → Session → Antwort → Mastery; Lehrer sieht Stand | API (+ Frontend) | TST-4 |

**Zielbild am Ende von E12:** `uv run pytest -q` läuft grün in CI; ein **vorgelagerter** Safety-Schritt (`test_rls.py` + `test_cohort_threshold.py`) bricht den Build sofort ab, wenn die Zeilenisolation oder die Min-Cohort-Schwelle reisst; Unit-Tests für BKT/Grader/Parser/Anonymizer laufen schnell ohne DB; ein voller Agent-Turn beweist operativ, dass `assess` deterministisch ist (Konfidenz 1.0, P2) und das **Learner-Modell** sich ändert (nicht der Agent, P3); ein HTTP-E2E-Smoke beweist die Präsentations-Trennung (Schüler ohne `uncertainty`, Lehrer mit, P5).

**Grundsätze (aus docs/10 §1):**
- Tests gegen **echtes Postgres mit aktivierter RLS** — gegen SQLite würde die wichtigste Eigenschaft (Zeilenisolation) gar nicht geprüft.
- Unit-Tests reiner Logik (BKT/Grader/Parser/Anonymizer) brauchen **keine** DB und müssen schnell sein.
- Safety-Tests blockieren den Merge (P1).

## 2. Task-Reihenfolge & Abhängigkeiten

```
FND-6 (CI) ─┐
DB-3 (scoped_session) ─┴─► TST-1 (conftest.py: Test-DB-Fixture + DBFactory + two_students)
                                 │
                                 ├─► [SAF-4: test_rls.py + test_cohort_threshold.py laufen auf diesen Fixtures]
                                 │     (gehört zu E3, aber abhängig von TST-1-Fixtures + CI-Gate aus TST-?)
                                 │
LM-1 + GR-2 ───────────────────► TST-2 (Unit: test_bkt.py, test_grading/, parser, anonymize)  [DB-frei, parallel zu TST-1]
                                 │
AG-2 ──────────────────────────► TST-3 (Integration: test_agent_turn.py)  [braucht TST-1-Fixtures + Test-DB]
                                 │
API-2 + FE-T2 ─────────────────► TST-4 (E2E-Smoke: HTTP zwingend, Browser optional)  [braucht TST-1-Fixtures + laufende API]
```

Kompakt:
- **TST-1** ist das Fundament: ohne `conftest.py`/`DBFactory` laufen weder die Safety-Tests noch TST-3/TST-4 gegen die DB. Hängt an **FND-6** (CI-Skelett, das erweitert wird) und **DB-3** (`scoped_session`, das die `DBFactory` spiegelt).
- **TST-2** ist DB-frei und kann **parallel** zu TST-1 entstehen; braucht aber `LM-1` (BKT) und `GR-2` (Math-Grader) als Testgegenstand.
- **TST-3** braucht TST-1 (Fixtures + Test-DB) und `AG-2` (Nodes/Graph).
- **TST-4** braucht TST-1, eine lauffähige API (`API-2`) und die Lehrer-Panel-Datenform (`FE-T2`).
- Der **blockierende CI-Schritt** für die Safety-Tests wird in E12 verdrahtet (docs/10 §7) — er ist die organisatorische Klammer um SAF-4.

## 3. Feinere Sub-Task-Zerlegung (über die Issues hinaus)

**TST-1 (Fixtures):**
- `engine`-Fixture (`scope="session"`): Engine aus `DATABASE_URL`, dann **Alembic `upgrade head`** inkl. `rls.sql`-Migration gegen die Test-DB.
- `db`-Fixture: Connection + äussere Transaktion + Session, am Ende **Rollback** (Test-Isolation).
- `DBFactory`: `_as(pg_role, student_id, teacher_id, allow_unscoped)`; `as_student/as_teacher/as_admin`; **fail-closed** (Schüler ohne `student_id` und ohne `allow_unscoped` → `PermissionError`).
- `db_factory`-Fixture und `two_students`-Fixture (zwei Schüler + 1 Skill + je 1 Attempt, als Setup-Pfad).
- **Zusatz-Sub-Task:** `seeded_student_and_item`-Fixture (wird von TST-3 referenziert, ist in docs/10 §5 vorausgesetzt aber **nicht definiert** → siehe offene Fragen).
- **Zusatz-Sub-Task:** `DATABASE_URL`-Guard, der Tests mit klarer Meldung abbricht, wenn keine echte Postgres-URL gesetzt ist (verhindert versehentliches SQLite).
- **Zusatz-Sub-Task:** Entscheidung Alembic sync vs. async (env.py), damit `command.upgrade` im Test deterministisch läuft.

**TST-2 (Unit):**
- `test_bkt.py`: `posterior` in `[0,1]`, Monotonie (mehr Korrekte → höhere Mastery), Korrekt-vs-Falsch-Ordnung; optional bekannte Referenzwerte für eine kurze Sequenz.
- `test_grading/test_math.py`: äquivalente Formen akzeptiert, falsche zurückgewiesen mit `confidence == 1.0`.
- `test_grading/__init__.py` (Package-Marker), ggf. `test_grading/conftest.py` falls geteilte Grader-Fixtures sinnvoll.
- `test_content_parser.py`: Prosa/Code-Trennung, Wikilink-Extraktion.
- `test_anonymize.py`: Name/Datum/E-Mail werden ersetzt (P4).
- **Zusatz-Sub-Task:** Registry-Test (`get_grader("math")` liefert `MathGrader`, unbekanntes Fach → `LookupError`) — sichert die einzige Plugin-Naht (P7) ab.

**TST-3 (Integration):**
- `test_agent_turn.py`: voller `ANSWER`-Turn in `db_factory.as_student(...)`; Assertions: `grade is not None`, `grade["confidence"] == 1.0` (P2), `mastery is not None` (P3).
- **Zusatz-Sub-Task:** Negativfall „niedrige Konfidenz wird nicht zementiert" (P6) — ein Turn mit Grader-Konfidenz < 0.9 darf `learner_state` **nicht** verändern (sofern ein solcher Grader/Item verfügbar ist).
- **Zusatz-Sub-Task:** Session-Injektion klären — `update_model_node` öffnet im Doc-Stub ein eigenes `SessionLocal()`; der Test läuft aber in `db_factory.as_student(...)`. Konflikt auflösen (siehe offene Fragen/Risiken).

**TST-4 (E2E-Smoke):**
- HTTP-Smoke (zwingend): `httpx`-Client gegen die laufende API; Schüler-Token → `POST /student/turn`, dann `GET /student/mastery`; Lehrer-Token → `GET /teacher/student/{id}/mastery`; konsistente Werte; Lehrer-Antwort enthält `uncertainty`, Schüler-Antwort nicht.
- Browser-E2E (optional, je nach Reifegrad): Playwright — Mastery-Bar steigt; Lehrer-Panel zeigt Unsicherheit; kleine Kohorte zeigt „zu wenige Lernende".
- **Zusatz-Sub-Task:** Token-Beschaffung im Test klären — `current_principal` ist in FND-5 noch ein Stub (`NotImplementedError`); der Smoke braucht eine testbare Auth (siehe offene Fragen).

**CI (docs/10 §7):**
- `ci.yml` (aus FND-6) erweitern: **Safety-Gate-Schritt** (`uv run pytest tests/test_rls.py tests/test_cohort_threshold.py -q`) **vor** dem Full-Suite-Schritt; beide mit `working-directory: apps/api`.
- Sicherstellen, dass Migrationen inkl. `rls.sql` im CI gegen den Postgres-Service angewandt werden (über die `engine`-Fixture beim ersten DB-Test).

## 4. Zentrale Designentscheidungen mit Begründung

1. **Echtes Postgres, kein SQLite.** Die zentrale Garantie ist Zeilenisolation via RLS — die existiert in SQLite nicht. Tests, die RLS umgehen, wären ein falsches Sicherheitsgefühl (P1). Daher `DATABASE_URL` auf einen pgvector-Service, in CI als Service-Container.
2. **Transaktion-pro-Test mit Rollback.** Jeder Test bekommt eine isolierte Sicht; am Ende Rollback statt Truncate → schnell und nebenwirkungsfrei. Konsequenz: Tests dürfen nicht selbst committen (sonst bricht die Isolation) — relevant für TST-3, dessen Schreibpfad committed (siehe Risiken).
3. **`DBFactory` als Test-Spiegel von `scoped_session` (DB-3).** Bewusst gewählt, damit die Tests **exakt** den Rollen-/Variablen-Mechanismus (`SET ROLE`, `SET app.current_student_id`) prüfen, auf dem die RLS-Policies beruhen — nicht eine vereinfachte Attrappe. Die `fail-closed`-Logik (Schüler ohne `student_id` → Fehler) spiegelt `scoped_session` 1:1.
4. **Safety-Gate vorgelagert und separat.** Ein eigener, **vorgeschalteter** CI-Schritt macht im Log sofort sichtbar, wenn die Isolationsgarantien brechen — bevor die übrige Suite überhaupt läuft (docs/10 §7). Das ist Sicherheitsarchitektur, kein Reporting (P6-Geist).
5. **Unit-Tests DB-frei und schnell.** BKT/Grader/Parser/Anonymizer sind reine Funktionen — sie brauchen keine DB und liefern schnelles Feedback. Das hält die Pyramide gesund (viele schnelle Unit-Tests, wenige langsame E2E).
6. **Agent-Turn prüft Prinzipien operativ.** Statt nur „läuft durch" prüft TST-3 die zwei tragenden Prinzipien als Assertions: `confidence == 1.0` (kuratiert, P2) und `mastery is not None` (Modell aktualisiert sich, P3).
7. **HTTP-Smoke vor Browser-E2E.** Der HTTP-Smoke ist schnell, deterministisch und prüft die Präsentations-Trennung (P5) direkt an der API-Grenze; Playwright ist optional und reifegradabhängig.
8. **`uv`-only.** Alle Testläufe über `uv run pytest` — niemals `pip` (P9, docs/00 §8).

## 5. Risiken & Gegenmassnahmen

| Risiko | Gegenmassnahme |
|---|---|
| **Transaktions-Rollback vs. Commit im Agent-Turn:** `update_model_node` ruft `s.commit()` (docs/07). Die `db`-Fixture erwartet aber, dass nichts committed wird (Rollback-Isolation). Ein Commit innerhalb der äusseren Transaktion kann die Isolation brechen oder die Assertions verfälschen. | TST-3 nutzt **nicht** die `db`-Rollback-Fixture, sondern `db_factory.as_student(...)` (eigene Session) und räumt explizit auf (oder nutzt eine Savepoint-Strategie). Session-Injektion in `update_model_node` klären, damit der Node die Test-Session verwendet statt ein eigenes `SessionLocal()`. |
| **`seeded_student_and_item`-Fixture undefiniert:** TST-3 referenziert sie (docs/10 §5), aber sie ist nirgends spezifiziert. | In TST-1 definieren: legt Schüler + Skill + kuratiertes Item (`item_ref`, `answer_key`) so an, dass der Math-Grader es bewerten kann. Item-Quelle = `content/items.py`/`load_item` (siehe offene Fragen). |
| **`load_item`/`content/items.py` fehlt:** `assess_node` lädt das Item via `load_item(item_ref)` (docs/07), aber `content/items.py` ist in keinem Doc spezifiziert. Ohne sie kann TST-3 nicht laufen. | Als Vorbedingung markieren; Test mit einem Minimal-`load_item` oder einem Monkeypatch arbeiten lassen, bis `content/items.py` definiert ist. Offene Frage eskalieren. |
| **Auth-Stub blockiert E2E:** `current_principal` wirft `NotImplementedError` (FND-5). Der HTTP-Smoke braucht echte Token. | Test-Auth-Override per FastAPI `dependency_overrides` (Test-Principal injizieren) **oder** ein Test-JWT mit `settings.jwt_public_key`. Entscheidung treffen (siehe offene Fragen). |
| **CI-DB ohne pgvector/Extensions:** RLS-Migration oder Vektor-Spalten schlagen fehl, wenn `vector`/`uuid-ossp` nicht installiert sind. | `engine`-Fixture/CI-Schritt installiert Extensions (FND-6 macht das bereits für `vector`); ggf. `uuid-ossp` ergänzen. |
| **Alembic sync vs. async unklar (docs/03 §6):** `command.upgrade` in der `engine`-Fixture verhält sich je nach `env.py` unterschiedlich. | Eine Variante festlegen (Empfehlung: sync für Migrationen/Tests). Offene Frage. |
| **Safety-Gate umgehbar:** Wenn der Safety-Schritt nur Teil der Full-Suite ist, kann ein Skip ihn aushebeln. | Eigener, **vorgelagerter** Schritt mit explizit benannten Dateien (docs/10 §7); kein `-k`/Skip-Mechanismus, der die Safety-Tests überspringt. |
| **Flaky E2E (Browser):** Playwright-Tests sind anfällig für Timing. | HTTP-Smoke als **zwingend** (CI-relevant), Browser-E2E als optional/nicht-blockierend führen, bis stabil. |

## 6. Offene Fragen / zu treffende Entscheidungen

1. **`seeded_student_and_item` / `load_item` / `content/items.py`:** Diese Fixture und die Item-Ladefunktion werden von TST-3 vorausgesetzt, sind aber nirgends spezifiziert. Wo kommen kuratierte Items mit `answer_key` her? (Inline in der Fixture, aus einer Tabelle, aus dem Vault?)
2. **Session-Injektion in `update_model_node`:** Der Doc-Stub öffnet ein eigenes `SessionLocal()` „in der Praxis: die request-scoped Session injizieren". Wie wird die Test-Session (aus `db_factory.as_student`) in den Node gereicht, damit RLS-Kontext und Transaktion stimmen?
3. **Test-Auth für den HTTP-Smoke:** `current_principal` ist Stub. `dependency_overrides` mit Test-Principal oder echtes Test-JWT?
4. **Alembic sync vs. async** (env.py) — wirkt direkt auf die `engine`-Fixture.
5. **Commit/Rollback-Strategie für TST-3:** Savepoint-basierte Isolation oder eigene Session mit explizitem Teardown?
6. **Browser-E2E (Playwright) jetzt oder später?** docs/10 §6 lässt beide Varianten zu; was ist für M6 verbindlich?

## 7. Test-/Verifikationsstrategie für das Epic

- **Lokal:**
  - DB hochfahren: `docker compose -f infra/docker-compose.yml up -d`
  - `DATABASE_URL` setzen (z. B. `postgresql+psycopg://its:its_dev_pw@localhost:5432/its`).
  - In `apps/api`: `uv sync`
  - Safety-Gate zuerst: `uv run pytest tests/test_rls.py tests/test_cohort_threshold.py -q` → alle grün.
  - Unit (DB-frei, schnell): `uv run pytest tests/test_bkt.py tests/test_grading/ tests/test_content_parser.py tests/test_anonymize.py -q`
  - Integration: `uv run pytest tests/test_agent_turn.py -q`
  - E2E-Smoke (HTTP): API starten (`uv run uvicorn its.main:app`) und `uv run pytest tests/e2e/ -q`.
  - Volle Suite: `uv run pytest -q`.
- **CI (docs/10 §7):** Postgres-Service-Container; `vector`-Extension installiert; zwei Schritte — (1) Safety-Gate (blockierend, vorgelagert), (2) Full Suite. Build rot ⇒ Merge blockiert.
- **Akzeptanz auf Epic-Ebene (docs/10 §8):** `conftest.py` mit transaktionaler Test-DB + `DBFactory`; Migrationen inkl. `rls.sql` angewandt; BKT/Grading-Unit-Tests grün, Parser/Anonymizer getestet; Agent-Turn-Test (Konfidenz 1.0 + Mastery aktualisiert); E2E-HTTP-Smoke grün; Safety-Tests als vorgelagerter, blockierender CI-Schritt.
