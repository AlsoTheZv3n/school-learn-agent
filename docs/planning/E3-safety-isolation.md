# E3 — Safety & Isolation (RLS + Min-Cohort) — Detailplanung

> Milestone: **M1 Data Layer & Safety**. Quelldokument: `docs/04-safety.md`. Querbezuege: `docs/00-architecture.md` (Prinzipien P1-P9, Repo-Layout Section 6, DoD Section 8), `docs/03-database.md` (Schema + `scoped_session`, DB-3), `docs/02-foundations.md` (FND-5 Auth-Geruest, `config.py`), `docs/10-testing.md` (Fixtures fuer SAF-4), `docs/05-retrieval.md` / `docs/08-backend-api.md` (nachgelagerte Konsumenten).

## 1. Scope & Zielbild

E3 verankert die Sicherheit dieses ITS fuer Minderjaehrige dort, wo sie nicht umgangen werden kann: **in der Datenbank** (P1). Es schliesst die zwei Leck-Flaechen zwischen Personen, die ein System mit "erzaehl mir ueber *mich*" und "erzaehl mir ueber *alle*" zwangslaeufig hat:

1. **Individual-Leak** — eine Query, die haette gescoped sein sollen, liefert fremde Schuelerzeilen. Gegenmassnahme: **Postgres Row-Level Security (RLS)** (SAF-1) plus ein **Scoping-Resolver** (SAF-2) als zweite, anwendungsseitige Schranke.
2. **Aggregat-Leak** — eine "Population"-Query ueber einen Filter, der genau eine Person trifft, wird zur de-anonymisierten Einzelauskunft. Gegenmassnahme: **Min-Cohort-Schwelle** (SAF-3).

Beide Mechanismen sind **fail-closed**: Im Zweifel werden 0 Zeilen bzw. eine Verweigerung zurueckgegeben, nie "alle". SAF-4 beweist beide Eigenschaften mit **CI-blockierenden** Tests gegen echtes Postgres mit aktivierter RLS.

Zielzustand am Ende des Epics:
- `attempts`, `learner_state`, `teacher_notes`, `enrollments` haben RLS aktiviert; Schueler sehen ausschliesslich eigene Zeilen, Lehrer nur Zeilen der Schueler ihrer Klassen.
- Es existiert kein Codepfad, der eine Individual-Query ohne aufgeloesten Scope ausfuehrt (`ScopeError` statt "alle").
- Jede Population-/Aggregat-Antwort laeuft durch genau eine zentrale Schwellenpruefung (`enforce_min_cohort`, Default `k=10`).
- Die zwei Safety-Eigenschaften (Zeilenisolation, Min-Cohort) sind durch Tests bewiesen, die einen Merge blockieren, wenn sie brechen.

Nicht-Ziele von E3: Auth/JWT-Decoding (das ist FND-5, hier nur konsumiert), die Retrieval-Module selbst (E4/E5, sie *nutzen* SAF-2/3), die API-Endpunkte (E9, sie mappen die Exceptions auf 403).

## 2. Task-Reihenfolge & Abhaengigkeiten

Vorbedingung des gesamten Epics: **DB-3** (`scoped_session` mit Rollen-/`student_id`-Hook) und **FND-5** (`Role`, `Principal`, `PG_ROLE`) muessen stehen.

```
DB-3 ──┬──► SAF-1 (RLS-Policies + Rollen + Grants als Migration)
       │        │
FND-5 ─┘        ├──► SAF-2 (Scoping-Resolver)  [auch dep: FND-5 fuer Principal/Role]
       │        │
       └──────► SAF-3 (Min-Cohort-Schwelle)    [parallel zu SAF-1/2 moeglich]
                │
   SAF-1 + SAF-2 + SAF-3 ──► SAF-4 (Safety-Tests, CI-blockierend)
```

Empfohlene Bearbeitungsreihenfolge:
1. **SAF-1** zuerst — alles andere setzt die DB-Schranke voraus; ohne sie sind die Tests sinnlos.
2. **SAF-3** parallel moeglich (reine Funktion, keine DB-Kopplung ausser `settings`).
3. **SAF-2** parallel zu SAF-3 (haengt logisch an FND-5 und ergaenzt SAF-1 anwendungsseitig).
4. **SAF-4** zuletzt — beweist SAF-1/2/3 zusammen; schaltet das CI-Gate scharf.

Nachgelagert warten auf E3: **RET-3** (individual via SAF-2 + RLS), **RET-4** (population via SAF-3), **API-2/API-3** (Endpunkte + Exception-Handler `ScopeError`/`CohortTooSmall` → 403), **TST-1** (`conftest.py`-Fixtures spiegeln die Rollen-Variablen). Die `scoped_session`-Ergaenzung um `app.current_teacher_id` (Teil von SAF-1-Umsetzung gemaess docs/04 §2, technisch in `db/session.py`) ist Voraussetzung fuer die Teacher-RLS-Policies.

## 3. Feinere Sub-Task-Zerlegung (ueber die Issues hinaus)

**SAF-1 (RLS):**
- 1a. `safety/rls.sql` als versioniertes SQL-Artefakt anlegen (Rollen-DO-Block, Grants, `ENABLE ROW LEVEL SECURITY`, Student-/Teacher-Policies, Admin-Hinweis).
- 1b. Alembic-Migration `0002_rls_policies` schreiben, die `rls.sql` einliest und in `op.execute(...)` ausfuehrt; `downgrade()` mit `DROP POLICY`/`ALTER TABLE ... DISABLE ROW LEVEL SECURITY` (idempotent, falls moeglich).
- 1c. `db/session.py` (`scoped_session`) um den Teacher-Zweig erweitern: `SET app.current_teacher_id = :tid` fuer `Role.TEACHER`.
- 1d. Pruefen, dass `classes`/`teachers` aus DB-1 vorhanden sind (die Teacher-Policy joint `enrollments → classes`); `GRANT SELECT ON classes` fuer Lehrer ergaenzen, da die Policy-Subquery `classes` liest.
- 1e. `FORCE ROW LEVEL SECURITY` erwaegen, damit auch der Tabellen-Owner nicht versehentlich umgeht (zu entscheiden, siehe offene Fragen).
- 1f. Smoke gegen die Docker-DB: nach `alembic upgrade head` zeigt `\d+ attempts` "Row security: enabled".

**SAF-2 (Scoping-Resolver):**
- 2a. `safety/scoping.py` mit `ScopeError(PermissionError)`, `require_student_scope(principal)`, `teacher_id_of(principal)`.
- 2b. Sicherstellen, dass `require_student_scope` fail-closed ist: fehlende `student_id` oder Nicht-Student-Rolle → `ScopeError`.
- 2c. Unit-Tests fuer die drei Pfade (Student mit ID → ID; Student ohne ID → Error; Lehrer → Error).

**SAF-3 (Min-Cohort):**
- 3a. `safety/cohort.py` mit `CohortTooSmall(PermissionError)`, `CohortResult`-Dataclass (frozen), `enforce_min_cohort(n, payload, k=None)`.
- 3b. Default-`k` aus `settings.min_cohort_k` ziehen (bereits in `config.py` und `.env.example` mit `10` verankert).
- 3c. Pruefen, dass `<` (nicht `<=`) verwendet wird: `n == k` ist erlaubt, `n < k` wird verweigert.

**SAF-4 (Safety-Tests):**
- 4a. `tests/test_rls.py` (Isolation, eigene Zeilen, ungescoped → 0).
- 4b. `tests/test_cohort_threshold.py` (klein verweigert, ausreichend durch).
- 4c. CI: vorgelagerter, separater Safety-Schritt in `ci.yml`, der vor der vollen Suite laeuft und bei Rot blockiert (gemaess docs/10 §7).
- 4d. Voraussetzung: `conftest.py`-Fixtures (`db_factory`, `two_students`) — formal TST-1, aber fuer SAF-4 noetig; entweder hier mitliefern oder als harte Abhaengigkeit deklarieren (siehe offene Fragen).

## 4. Zentrale Designentscheidungen mit Begruendung

- **Isolation in der DB, nicht im App-Code (P1).** RLS macht die gefaehrliche Haelfte (Zeilensichtbarkeit) zu einer Schema-Eigenschaft. Selbst eine fehlerhaft generierte Query (z. B. vom Agenten) kann keine fremden Zeilen liefern. SAF-2 ist eine *zusaetzliche* Schranke, kein Ersatz.
- **Fail-closed via `current_setting(..., true)` + `NULLIF`.** Ist die Session-Variable nicht gesetzt, liefert der Ausdruck `NULL`; `student_id = NULL` ist nie wahr → 0 Zeilen statt aller Zeilen. Das ist der Kern der Sicherheitsgarantie und wird explizit getestet.
- **RLS als versionierte Migration.** RLS ist Schema; sie muss mit dem Schema wandern (Deploy, Test-DB, CI). `rls.sql` wird daher von Alembic ausgefuehrt, nicht haendisch.
- **Getrennte Session-Variablen pro Rolle.** `app.current_student_id` (Schueler) und `app.current_teacher_id` (Lehrer). Die Teacher-Policy keyt ueber den `enrollments → classes`-Join auf die Lehrer-Identitaet — so sieht ein Lehrer nur eigene Klassen.
- **Admin bewusst ohne pauschales `BYPASSRLS`.** Admin-Funktionen laufen ueber dedizierte, gepruefte Pfade; pauschaler Bypass waere ein offenes Scheunentor.
- **Genau eine zentrale Cohort-Schranke.** `enforce_min_cohort` ist die *einzige* Stelle, durch die Aggregate gehen (RET-4, API-2 rufen sie auf). Eine Stelle = ein Ort, der geprueft und auditiert werden muss.
- **Tests gegen echtes Postgres.** Gegen SQLite o. Ae. wuerde RLS gar nicht existieren — die wichtigste Eigenschaft bliebe ungeprueft. CI startet daher einen `pgvector/pgvector:pg16`-Service.
- **`uv`-only (P9).** Alle Test-/Migrations-Befehle laufen ueber `uv run ...`, niemals `pip`.

## 5. Risiken & Gegenmassnahmen

- **Owner umgeht RLS.** Postgres wendet RLS standardmaessig **nicht** auf den Tabellen-Owner an. Wenn der App-Login `its` zugleich Owner ist, koennten Policies wirkungslos sein. Gegenmassnahme: konsequentes `SET ROLE its_student/teacher` (kein Owner-Kontext) und Pruefung, ob `FORCE ROW LEVEL SECURITY` noetig ist; der Test `test_unset_scope_returns_no_rows` deckt einen stillen Bruch auf.
- **Test-Setup hebelt RLS aus.** Die Fixtures legen Daten als privilegierter Pfad an; wenn die Lese-Assertions versehentlich ebenfalls privilegiert laufen, testen sie nichts. Gegenmassnahme: Leseproben strikt ueber `db_factory.as_student/as_teacher`.
- **Vergessene Tabelle.** Eine spaeter hinzukommende PII-Tabelle ohne RLS leakt still. Gegenmassnahme: Konvention "neue PII-Tabelle = RLS-Policy in derselben Migration" plus Idee eines Meta-Tests, der prueft, dass alle als PII markierten Tabellen `relrowsecurity = true` haben.
- **`enforce_min_cohort` umgangen.** Eine Aggregat-Query, die die Funktion nicht aufruft, leakt. Gegenmassnahme: Konvention + Review; RET-4/API-2 rufen sie zentral auf; AK von RET-4 verlangt "ausschliesslich via `enforce_min_cohort`".
- **`<=` statt `<`.** Off-by-one wuerde `n == k` faelschlich verweigern oder `n < k` durchlassen. Gegenmassnahme: expliziter Test fuer Grenzwerte (`n=k-1` verweigert, `n=k` erlaubt) — empfohlene Ergaenzung.
- **CI-Gate uebersprungen.** Wenn der Safety-Schritt nicht separat/vorgelagert ist, faellt ein Bruch erst spaet auf. Gegenmassnahme: dedizierter, vorgelagerter `pytest tests/test_rls.py tests/test_cohort_threshold.py`-Schritt.

## 6. Offene Fragen / zu treffende Entscheidungen

1. **`FORCE ROW LEVEL SECURITY`** auf den geschuetzten Tabellen — ja/nein? Relevant, weil der App-User `its` laut docs Owner sein koennte und RLS sonst fuer ihn nicht greift. Empfehlung: ja, in SAF-1 mit aufnehmen.
2. **Migrationsnummer/-stil von SAF-1.** docs/04 sagt "von einer Alembic-Migration ausgefuehrt", aber Name/Nummer und sync-vs-async-`env.py` sind offen (docs/03 nennt beide). Empfehlung: `0002_rls_policies`, sync `env.py` fuer M1.
3. **Wer liefert `conftest.py` (TST-1) fuer SAF-4?** docs/10 verortet die Fixtures dort, docs/04 setzt sie voraus. Empfehlung: minimale Fixtures (`db_factory`, `two_students`) mit SAF-4 ausliefern und in TST-1 konsolidieren.
4. **`teacher_id_of` nutzt `principal.user_id`, RLS-Variable heisst `app.current_teacher_id`.** Wer setzt sie — `scoped_session` (docs/03) oder Aufrufer? Empfehlung: ausschliesslich `scoped_session`, analog zur Schueler-Variable.
5. **Grant auf `classes` fuer Lehrer.** Die Teacher-Policy-Subquery liest `classes`; in docs/04 §2 fehlt ein expliziter `GRANT SELECT ON classes`. Empfehlung: ergaenzen.
6. **Konkreter Wert/Tunbarkeit von `k`.** Default `10` ist gesetzt; ob pro Klasse/Fach uebersteuerbar, ist offen. Empfehlung: vorerst global, optionaler `k`-Parameter bleibt (bereits in der Signatur).

## 7. Test-/Verifikationsstrategie fuer das Epic

- **Echtes Postgres + RLS** (kein SQLite). CI startet `pgvector/pgvector:pg16` (FND-6) und wendet Migrationen **inkl. `rls.sql`** an (`alembic upgrade head`).
- **Vorgelagerter, blockierender Safety-Schritt** in `ci.yml`: `uv run pytest tests/test_rls.py tests/test_cohort_threshold.py -q` vor der vollen Suite (docs/10 §7).
- **RLS-Eigenschaften** (`tests/test_rls.py`): A sieht 0 Zeilen von B (`attempts`, `learner_state`); A sieht eigene (>0); Schueler-Session ohne `student_id` → 0 Zeilen.
- **Cohort-Eigenschaften** (`tests/test_cohort_threshold.py`): `n < k` → `CohortTooSmall`; `n >= k` → Payload durch; empfohlen zusaetzlich Grenzwert `n == k`.
- **Scoping-Unit** (empfohlen): `require_student_scope` fail-closed (Student ohne ID, Nicht-Student → `ScopeError`).
- **Lokale Verifikation:** `docker compose -f infra/docker-compose.yml up -d`, dann in `apps/api`: `uv sync`, `uv run alembic upgrade head`, `uv run pytest -q`. Manuell `psql ... -c "\d+ attempts"` → "Row security: enabled".
