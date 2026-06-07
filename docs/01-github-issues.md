# 01 — GitHub: Milestones, Epics & Issues

> **Claude Code: Das hier ist Schritt 1, noch vor jedem Code.** Lege Labels, Milestones,
> Epics und Issues an. Diese Datei ist die **Quelle der Wahrheit**. Nutze das Bootstrap-Skript
> am Ende (`gh` CLI). Danach folgt die Umsetzung gemäss Dokumenten 02–11.

---

## 1. Phasen (Milestones)

Strikte Reihenfolge — Safety vor Features, die sie voraussetzen.

| Key | Milestone | Ziel | Enthält Epics |
|-----|-----------|------|----------------|
| **M0** | Foundations | Repo, Infra, Skeleton lauffähig | E1 |
| **M1** | Data Layer & Safety | Schema + RLS + Min-Cohort beweisbar dicht | E2, E3 |
| **M2** | Retrieval & Content | 3 Modi + Graph + Vault-Ingestion | E4, E5 |
| **M3** | Learning Engine | Lernmodell + Bewertung + Agent-Loop | E6, E7, E8 |
| **M4** | API & Frontend | Endpoints + Schüler-/Lehrer-UI | E9, E10, E11 |
| **M5** | Data & Production | Mock-Seeder + Produktionsdaten + Compliance | E13, E14 |
| **M6** | Hardening | Querschnitt-Tests, CI, Audit | E12 |

> Hinweis: E12 (Testing/CI) wird **früh aufgesetzt** und **kontinuierlich** gefüllt; der
> Milestone M6 schliesst die übergreifende Härtung ab. Safety-Tests entstehen aber bereits in M1.

---

## 2. Labels

```
# Typ
type:feature        type:infra        type:test        type:docs        epic
# Bereich
area:db             area:safety       area:retrieval   area:content
area:agent          area:learner-model area:grading    area:backend
area:frontend       area:data         area:auth        area:llm
# Priorität / Sonder
priority:critical   safety-critical   good-first-issue  blocked
```

`safety-critical` markiert Issues, deren Bruch Schülerdaten leaken würde. Diese brauchen
zwingend Tests und Review.

---

## 3. Epics

Jedes Epic ist ein GitHub-Issue mit Label `epic`, das eine **Checkliste** seiner Task-Issues
enthält. Mapping zu den Detaildokumenten:

| Epic | Titel | Dok | Milestone |
|------|-------|-----|-----------|
| **E1** | Foundations: Monorepo, Infra, Skeleton | 02 | M0 |
| **E2** | Database: Schema & Migrationen | 03 | M1 |
| **E3** | Safety & Isolation (RLS + Min-Cohort) | 04 | M1 |
| **E4** | Retrieval: Router + 3 Modi + Graph | 05 | M2 |
| **E5** | Content-Ingestion (Markdown-Vault) | 05 | M2 |
| **E6** | Learner-Modell (BKT) | 06 | M3 |
| **E7** | Grading-Strategy-Registry | 06 | M3 |
| **E8** | Agent-Loop (LangGraph) | 07 | M3 |
| **E9** | Backend-API (Student + Teacher) | 08 | M4 |
| **E10** | Frontend: Schüler-Session | 09 | M4 |
| **E11** | Frontend: Lehrer-Dashboard | 09 | M4 |
| **E12** | Testing & CI | 10 | M6 |
| **E13** | Mock-Data-Seeder | 11 | M5 |
| **E14** | Produktionsdaten & Compliance | 11 | M5 |

---

## 4. Issue-Inventar

Stabile Keys zur Referenz in den Dokumenten. Jedes Issue: Titel · Akzeptanzkriterien (AK) ·
Labels · Abhängigkeiten.

### E1 — Foundations (M0)

- **FND-1 — Monorepo-Grundgerüst anlegen**
  AK: `apps/api`, `apps/web`, `content/`, `infra/`, `tests/` vorhanden; Root-`README`; `.editorconfig`; `.gitignore`.
  Labels: `type:infra area:backend`
- **FND-2 — Python-Projekt mit `uv` initialisieren**
  AK: `apps/api/pyproject.toml` + `uv.lock`; FastAPI, SQLAlchemy, Alembic, Pydantic, psycopg, pytest als Deps; `uv run` startet die App. **Kein `pip`.**
  Labels: `type:infra area:backend` · dep: FND-1
- **FND-3 — Docker-Compose: Postgres + pgvector**
  AK: `infra/docker-compose.yml` startet Postgres 16 mit `pgvector`-Extension; Healthcheck; `.env.example` mit DB-URL.
  Labels: `type:infra area:db` · dep: FND-1
- **FND-4 — FastAPI-Skeleton + Healthcheck**
  AK: `src/its/main.py` App-Factory; `GET /health` → `{"status":"ok"}`; `src/its/config.py` (Pydantic-Settings).
  Labels: `type:feature area:backend` · dep: FND-2
- **FND-5 — Auth-Rollen-Gerüst (student/teacher/admin)**
  AK: `src/its/auth/roles.py` (Enum); `auth/deps.py` mit `current_principal()`-Dependency (vorerst Stub/JWT-Decode); definiert, wie die Rolle später RLS speist (siehe 04).
  Labels: `type:feature area:auth` · dep: FND-4
- **FND-6 — CI-Grundgerüst (GitHub Actions)**
  AK: Workflow `ci.yml` startet Postgres-Service, läuft `uv run pytest`; blockiert bei rot.
  Labels: `type:infra type:test` · dep: FND-2, FND-3

### E2 — Database (M1)

- **DB-1 — Kern-Schema-Migration**
  AK: Alembic-Migration erstellt Tabellen `students`, `teachers`, `classes`, `enrollments`, `subjects`, `skills`, `skill_edges`, `attempts`, `learner_state`, `teacher_notes`, `content_notes`, `content_embeddings`. Siehe Schema in 03.
  Labels: `type:feature area:db priority:critical` · dep: FND-3
- **DB-2 — SQLAlchemy-Modelle**
  AK: `src/its/db/models.py` deckt alle Tabellen ab; Typisierung; Relationen; `pgvector`-Spalte für Embeddings.
  Labels: `type:feature area:db` · dep: DB-1
- **DB-3 — Session-/Engine-Setup mit Rollen-Hook**
  AK: `src/its/db/session.py`; pro Request wird die DB-Rolle/`SET app.current_student_id` gesetzt (Vorbereitung für RLS, 04).
  Labels: `type:feature area:db safety-critical` · dep: DB-2
- **DB-4 — Skill-Graph-Seed (Fach Mathematik, Demo)**
  AK: Migration/Seed legt einen kleinen Skill-Graphen (z. B. „Quadratische Gleichungen") inkl. `skill_edges` an.
  Labels: `type:feature area:db good-first-issue` · dep: DB-1

### E3 — Safety & Isolation (M1) · alle `safety-critical`

- **SAF-1 — RLS-Policies (Schüler sieht nur eigene Zeilen)**
  AK: `src/its/safety/rls.sql` als versionierte Migration; Policies auf `attempts`, `learner_state`, `teacher_notes`, `enrollments`; Rollen `its_student`, `its_teacher`, `its_admin`.
  Labels: `type:feature area:safety priority:critical safety-critical` · dep: DB-3
- **SAF-2 — Scoping-Resolver**
  AK: `src/its/safety/scoping.py` übersetzt das authentifizierte Principal in die DB-Rolle + `student_id`-Kontext; eine Individual-Query ohne Scope ist unmöglich (fail-closed).
  Labels: `type:feature area:safety safety-critical` · dep: SAF-1, FND-5
- **SAF-3 — Min-Cohort-Schwelle für Aggregate**
  AK: `src/its/safety/cohort.py`; `enforce_min_cohort(n, k)` verweigert Aggregate mit `n < k` (Default `k=10`, konfigurierbar); zentrale Stelle, durch die *jede* Population-Query läuft.
  Labels: `type:feature area:safety safety-critical` · dep: DB-3
- **SAF-4 — Safety-Tests (CI-blockierend)**
  AK: `tests/test_rls.py` beweist: Schüler A kann Zeilen von B **nicht** lesen; `tests/test_cohort_threshold.py` beweist: Kohorte < `k` wird verweigert. Beide laufen in CI und blockieren Merge.
  Labels: `type:test area:safety priority:critical safety-critical` · dep: SAF-1, SAF-2, SAF-3

### E4 — Retrieval (M2)

- **RET-1 — Retrieval-Router**
  AK: `src/its/retrieval/router.py`; entscheidet Scope (semantic/individual/population) + ob Eskalation auf Live-Query nötig; auditierbar (geloggte Entscheidung).
  Labels: `type:feature area:retrieval` · dep: SAF-2, SAF-3
- **RET-2 — Semantic-Modus (pgvector)**
  AK: `retrieval/semantic.py`; Ähnlichkeitssuche über `content_embeddings`; gibt Prosa-Chunks + zugeordnete Sidecar-Query-Metadaten zurück.
  Labels: `type:feature area:retrieval` · dep: DB-2, CON-2
- **RET-3 — Individual-Modus (scoped)**
  AK: `retrieval/individual.py`; Query immer auf einen `student_id` gescoped (über SAF-2); niemals ohne Scope ausführbar.
  Labels: `type:feature area:retrieval safety-critical` · dep: SAF-2
- **RET-4 — Population-Modus (Aggregate)**
  AK: `retrieval/population.py`; `GROUP BY`-Aggregate **ausschliesslich** via `cohort.py`.
  Labels: `type:feature area:retrieval safety-critical` · dep: SAF-3
- **RET-5 — Graph-Traversal (rekursive CTE)**
  AK: `retrieval/graph.py`; Traversal über `skill_edges`/Note-Links per rekursiver CTE; Tiefenlimit.
  Labels: `type:feature area:retrieval` · dep: DB-2

### E5 — Content-Ingestion (M2)

- **CON-1 — Markdown-Parser (Prosa/Code-Split)**
  AK: `content/parser.py`; trennt Prosa von ```sql/```cypher-Codeblöcken; extrahiert `[[wikilinks]]` als Kanten.
  Labels: `type:feature area:content` · dep: FND-2
- **CON-2 — Ingestion-Pipeline (Embeddings)**
  AK: `content/ingest.py`; embeddet **nur Prosa**, Query bleibt Sidecar-Metadatum; schreibt `content_notes` + `content_embeddings` + Link-Kanten.
  Labels: `type:feature area:content` · dep: CON-1, DB-2
- **CON-3 — Demo-Vault**
  AK: `content/math/quadratic-equations.md` (Prosa + ```sql-Block) + `content/math/_links.md`.
  Labels: `type:docs area:content good-first-issue` · dep: —

### E6 — Learner-Modell (M3)

- **LM-1 — BKT-Kern**
  AK: `learner_model/bkt.py` (NumPy); vier Parameter pro Skill (prior/learn/slip/guess); reines, getestetes Update.
  Labels: `type:feature area:learner-model` · dep: FND-2
- **LM-2 — Tracing-Service**
  AK: `learner_model/tracing.py`; nimmt ein `attempt`-Resultat, aktualisiert `learner_state` (Mastery + Unsicherheit) pro Skill.
  Labels: `type:feature area:learner-model` · dep: LM-1, DB-2
- **LM-3 — DKT-Platzhalter**
  AK: `learner_model/dkt.py` mit Interface-kompatiblem Stub + Doku „erst bei ausreichend Daten".
  Labels: `type:docs area:learner-model` · dep: LM-2

### E7 — Grading (M3) · Plugin-Naht (P7)

- **GR-1 — `GraderStrategy`-Protokoll + Registry**
  AK: `grading/base.py` (Protocol: `grade(answer, item) -> GradeResult`); `grading/registry.py` keyt auf Fach.
  Labels: `type:feature area:grading` · dep: FND-2
- **GR-2 — Math-Grader (symbolisch/numerisch)**
  AK: `grading/math.py`; nutzt kuratierten Answer Key + symbolische Prüfung (z. B. `sympy`); **keine** freie LLM-Generierung des Schlüssels.
  Labels: `type:feature area:grading priority:critical` · dep: GR-1
- **GR-3 — Language- & History-Grader (Grundgerüst)**
  AK: `grading/language.py`, `grading/history.py`; Language regelbasiert; History offene Antwort (Rubric-gestützt, LLM nur als *Vorschlag* mit Lehrer-Override).
  Labels: `type:feature area:grading` · dep: GR-1

### E8 — Agent (M3)

- **AG-1 — LangGraph-State + Graph**
  AK: `agent/state.py` (State-Schema); `agent/graph.py` verdrahtet Nodes: route → retrieve → assess → update_model → explain.
  Labels: `type:feature area:agent` · dep: RET-1, LM-2, GR-1
- **AG-2 — Nodes**
  AK: `agent/nodes/{route,retrieve,assess,update_model,explain}.py`; `assess` nutzt Grader (kuratiert, P2), `explain` ist der generative Pfad.
  Labels: `type:feature area:agent` · dep: AG-1
- **AG-3 — LLM-Client + Anonymisierung**
  AK: `llm/client.py` (Frontier **oder** lokal, per Config); `llm/anonymize.py` entfernt PII vor jedem externen Call (P4); `llm/prompts/`.
  Labels: `type:feature area:llm safety-critical` · dep: FND-4

### E9 — Backend-API (M4)

- **API-1 — Student-Endpoints**
  AK: `api/student.py`; Session starten, Frage holen, Antwort einreichen (→ `assess` → `update_model`), Erklärung/Hint anfordern; alle scoped via SAF-2.
  Labels: `type:feature area:backend safety-critical` · dep: AG-1, SAF-2
- **API-2 — Teacher-Endpoints**
  AK: `api/teacher.py`; Open Learner Model lesen (inkl. Unsicherheit), Kohorten-Sicht (via cohort.py), Notiz/Intervention schreiben.
  Labels: `type:feature area:backend safety-critical` · dep: API-1, RET-4
- **API-3 — Pydantic-Schemas + Fehlermodell**
  AK: Request/Response-Schemas; einheitliche Fehlerantworten; Validierung speist sichere Query-Templates.
  Labels: `type:feature area:backend` · dep: FND-4

### E10 — Frontend Schüler (M4)

- **FE-S1 — React/TS-Projekt-Setup**
  AK: `apps/web` mit Vite + TS; `api/client.ts`; Routing student/teacher getrennt.
  Labels: `type:infra area:frontend` · dep: FND-1
- **FE-S2 — Session-Screen**
  AK: `web/src/student/SessionScreen.tsx` + `TutorThread.tsx` + `MasteryBar.tsx`; ein Konzept zur Zeit; Mastery **schonend** dargestellt (nicht die Rohschätzung).
  Labels: `type:feature area:frontend` · dep: FE-S1, API-1
- **FE-S3 — Helfer-Aktionen**
  AK: „Anders erklären / Hinweis / Wozu?" rufen den `explain`-Pfad; klar getrennt vom Bewertungspfad.
  Labels: `type:feature area:frontend` · dep: FE-S2

### E11 — Frontend Lehrer (M4)

- **FE-T1 — Dashboard-Shell**
  AK: `web/src/teacher/Dashboard.tsx`; Klassen-/Schülerliste; Einstieg in Detail.
  Labels: `type:feature area:frontend` · dep: FE-S1, API-2
- **FE-T2 — Learner-Model-Panel (Open Learner Model)**
  AK: `LearnerModelPanel.tsx` zeigt Mastery **inkl. Unsicherheit** pro Skill; macht „warum" sichtbar (P5).
  Labels: `type:feature area:frontend` · dep: FE-T1, API-2
- **FE-T3 — Interventions-Steuerung**
  AK: `InterventionControls.tsx`; Notiz hinterlegen, Einschätzung überschreiben (P6); Schüler-Screen zeigt die Notiz an.
  Labels: `type:feature area:frontend` · dep: FE-T2

### E12 — Testing & CI (kontinuierlich, Abschluss M6)

- **TST-1 — Pytest-Fixtures (DB pro Test, Rollen)**
  AK: `tests/conftest.py`; transaktionale Test-DB; Fixtures für student/teacher/admin-Rollen.
  Labels: `type:test` · dep: FND-6, DB-3
- **TST-2 — Unit-Tests Lernmodell & Grading**
  AK: `tests/test_bkt.py`, `tests/test_grading/`; BKT-Update korrekt; Math-Grader gegen kuratierten Key.
  Labels: `type:test area:learner-model area:grading` · dep: LM-1, GR-2
- **TST-3 — Integrationstests Agent-Loop**
  AK: ein voller Turn (Frage → Antwort → Mastery-Update) end-to-end gegen Test-DB.
  Labels: `type:test area:agent` · dep: AG-2
- **TST-4 — E2E Smoke (API + Frontend)**
  AK: Playwright/HTTP-Smoke: Login → Session → Antwort → Mastery sichtbar; Lehrer sieht Stand.
  Labels: `type:test area:frontend area:backend` · dep: API-2, FE-T2

### E13 — Mock-Data-Seeder (M5)

- **MOCK-1 — Seeder-CLI**
  AK: `scripts/seed.py` (uv-Entrypoint); `--profile demo|load|empty`; legt Klassen, Schüler, Skills, realistische `attempts` + abgeleitete `learner_state` an.
  Labels: `type:feature area:data` · dep: DB-2, LM-2
- **MOCK-2 — Realistische Lernkurven**
  AK: Attempts erzeugen plausible Mastery-Verläufe (nicht uniform); Kohorten gross genug für Aggregat-Tests (≥ `k`).
  Labels: `type:feature area:data` · dep: MOCK-1
- **MOCK-3 — Reset/Teardown**
  AK: `scripts/seed.py --reset` leert sicher (nur Dev-Umgebung; Guard gegen Prod).
  Labels: `type:feature area:data` · dep: MOCK-1

### E14 — Produktionsdaten & Compliance (M5)

- **PROD-1 — Produktiver Ingestion-Pfad**
  AK: `scripts/import_production.py`; importiert echtes Lernmaterial/echte Klassenlisten über validierte Schemata; Idempotenz; klare Trennung von Mock.
  Labels: `type:feature area:data` · dep: CON-2, DB-2
- **PROD-2 — Env-Toggle Mock/Prod + Guards**
  AK: `DATA_MODE=mock|prod`; Seeder in Prod gesperrt; getrennte DB-URLs.
  Labels: `type:feature area:data safety-critical` · dep: MOCK-1, PROD-1
- **PROD-3 — Datenresidenz & Retention**
  AK: Doku + Konfiguration: CH/EU-Region (P8), Aufbewahrungs-/Löschkonzept, Auftragsverarbeitung; rechtliche Angaben gegen aktuelle Quellen geprüft.
  Labels: `type:docs area:data priority:critical` · dep: —

---

## 5. Abhängigkeits-Reihenfolge (Kurzform)

```
FND-1 → FND-2/3 → FND-4 → FND-5 → FND-6
DB-1 → DB-2 → DB-3 ─┬→ SAF-1 → SAF-2
                    └→ SAF-3
SAF-2/3/4 → RET-1..5      CON-1 → CON-2
LM-1 → LM-2               GR-1 → GR-2/3
RET-1 + LM-2 + GR-1 → AG-1 → AG-2 (+ AG-3)
AG-1 → API-1 → API-2      FE-S1 → FE-S2/3   FE-T1 → FE-T2 → FE-T3
DB-2 + LM-2 → MOCK-1 → MOCK-2/3 → PROD-1/2
```

**Kritischer Pfad zuerst:** FND → DB → **SAF (inkl. SAF-4 Tests)** → Rest.

---

## 6. Bootstrap-Skript (`gh` CLI)

> Voraussetzung: `gh auth login` ist erfolgt und das Repo existiert (`gh repo create` oder bereits geklont).
> Claude Code: Lege das als `scripts/bootstrap_github.sh` ab und führe es aus. Das Skript ist
> idempotent genug für einen einmaligen Lauf; bei Wiederholung vorhandene Objekte ignorieren.

```bash
#!/usr/bin/env bash
set -euo pipefail

# --- Labels ---
create_label () { gh label create "$1" --color "$2" --description "$3" 2>/dev/null || true; }
create_label "epic"               "6f42c1" "Epic / tracking issue"
create_label "type:feature"       "1d76db" "Feature work"
create_label "type:infra"         "0e8a16" "Infrastructure / tooling"
create_label "type:test"          "fbca04" "Tests"
create_label "type:docs"          "c5def5" "Documentation"
create_label "area:db"            "5319e7" "Database"
create_label "area:safety"        "b60205" "Safety & isolation"
create_label "area:retrieval"     "0052cc" "Retrieval"
create_label "area:content"       "bfdadc" "Content ingestion"
create_label "area:agent"         "d93f0b" "Agent loop"
create_label "area:learner-model" "0e8a16" "Learner model"
create_label "area:grading"       "1d76db" "Grading"
create_label "area:backend"       "5319e7" "Backend API"
create_label "area:frontend"      "fbca04" "Frontend"
create_label "area:data"          "c2e0c6" "Data / seeding"
create_label "area:auth"          "d4c5f9" "Auth"
create_label "area:llm"           "f9d0c4" "LLM"
create_label "priority:critical"  "b60205" "Critical priority"
create_label "safety-critical"    "e11d21" "Breakage leaks student data"
create_label "good-first-issue"   "7057ff" "Good first issue"
create_label "blocked"            "000000" "Blocked by dependency"

# --- Milestones (via API) ---
create_ms () { gh api repos/{owner}/{repo}/milestones -f title="$1" -f description="$2" 2>/dev/null || true; }
create_ms "M0 Foundations"        "Repo, infra, skeleton"
create_ms "M1 Data Layer & Safety" "Schema + RLS + min-cohort"
create_ms "M2 Retrieval & Content" "3 modes + graph + ingestion"
create_ms "M3 Learning Engine"     "Learner model + grading + agent"
create_ms "M4 API & Frontend"      "Endpoints + student/teacher UI"
create_ms "M5 Data & Production"   "Seeder + production data + compliance"
create_ms "M6 Hardening"           "Cross-cutting tests, CI, audit"

# --- Helper: Issue anlegen ---
mk () { # mk "title" "milestone" "labels" "body"
  gh issue create --title "$1" --milestone "$2" --label "$3" --body "$4"
}

# --- Epics (Tracking-Issues) ---
mk "E1 Foundations" "M0 Foundations" "epic,type:infra" "Siehe docs/02-foundations.md. Tasks: FND-1..6."
mk "E2 Database" "M1 Data Layer & Safety" "epic,area:db" "Siehe docs/03-database.md. Tasks: DB-1..4."
mk "E3 Safety & Isolation" "M1 Data Layer & Safety" "epic,area:safety,safety-critical" "Siehe docs/04-safety.md. Tasks: SAF-1..4."
mk "E4 Retrieval" "M2 Retrieval & Content" "epic,area:retrieval" "Siehe docs/05-retrieval.md. Tasks: RET-1..5."
mk "E5 Content Ingestion" "M2 Retrieval & Content" "epic,area:content" "Siehe docs/05-retrieval.md. Tasks: CON-1..3."
mk "E6 Learner Model" "M3 Learning Engine" "epic,area:learner-model" "Siehe docs/06-learner-model-and-grading.md. Tasks: LM-1..3."
mk "E7 Grading" "M3 Learning Engine" "epic,area:grading" "Siehe docs/06-learner-model-and-grading.md. Tasks: GR-1..3."
mk "E8 Agent Loop" "M3 Learning Engine" "epic,area:agent" "Siehe docs/07-agent.md. Tasks: AG-1..3."
mk "E9 Backend API" "M4 API & Frontend" "epic,area:backend" "Siehe docs/08-backend-api.md. Tasks: API-1..3."
mk "E10 Frontend Student" "M4 API & Frontend" "epic,area:frontend" "Siehe docs/09-frontend.md. Tasks: FE-S1..3."
mk "E11 Frontend Teacher" "M4 API & Frontend" "epic,area:frontend" "Siehe docs/09-frontend.md. Tasks: FE-T1..3."
mk "E12 Testing & CI" "M6 Hardening" "epic,type:test" "Siehe docs/10-testing.md. Tasks: TST-1..4."
mk "E13 Mock Data Seeder" "M5 Data & Production" "epic,area:data" "Siehe docs/11-mock-data-and-production.md. Tasks: MOCK-1..3."
mk "E14 Production & Compliance" "M5 Data & Production" "epic,area:data" "Siehe docs/11-mock-data-and-production.md. Tasks: PROD-1..3."

# --- Task-Issues (Auszug; vollständige AK in den jeweiligen Docs) ---
# E1
mk "FND-1 Monorepo-Grundgerüst" "M0 Foundations" "type:infra,area:backend" "AK siehe docs/01 §4 (E1)."
mk "FND-2 uv-Projekt initialisieren" "M0 Foundations" "type:infra,area:backend" "AK siehe docs/01 §4 (E1). KEIN pip."
mk "FND-3 Docker-Compose Postgres+pgvector" "M0 Foundations" "type:infra,area:db" "AK siehe docs/01 §4 (E1)."
mk "FND-4 FastAPI-Skeleton + Healthcheck" "M0 Foundations" "type:feature,area:backend" "AK siehe docs/01 §4 (E1)."
mk "FND-5 Auth-Rollen-Gerüst" "M0 Foundations" "type:feature,area:auth" "AK siehe docs/01 §4 (E1)."
mk "FND-6 CI-Grundgerüst" "M0 Foundations" "type:infra,type:test" "AK siehe docs/01 §4 (E1)."
# E3 (safety zuerst sichtbar)
mk "SAF-1 RLS-Policies" "M1 Data Layer & Safety" "type:feature,area:safety,priority:critical,safety-critical" "AK siehe docs/04."
mk "SAF-2 Scoping-Resolver" "M1 Data Layer & Safety" "type:feature,area:safety,safety-critical" "AK siehe docs/04."
mk "SAF-3 Min-Cohort-Schwelle" "M1 Data Layer & Safety" "type:feature,area:safety,safety-critical" "AK siehe docs/04."
mk "SAF-4 Safety-Tests (CI-blockierend)" "M1 Data Layer & Safety" "type:test,area:safety,priority:critical,safety-critical" "AK siehe docs/04 + docs/10."

echo "Bootstrap abgeschlossen. Restliche Task-Issues (E2,E4..E14) analog ergänzen — Vorlage 'mk' oben."
```

> **Hinweis:** Das Skript legt alle Epics + die kritischen Foundation/Safety-Issues an. Die
> übrigen Task-Issues (DB-*, RET-*, CON-*, LM-*, GR-*, AG-*, API-*, FE-*, TST-*, MOCK-*, PROD-*)
> nach demselben `mk`-Muster ergänzen — die vollständigen Titel/Labels/Milestones stehen oben
> in §4. Wenn die GitHub-Sub-Issues-Funktion verfügbar ist, die Tasks zusätzlich als Sub-Issues
> unter ihr Epic hängen; andernfalls in der Epic-Beschreibung als Checkliste `- [ ] FND-1 …` führen.

---

## Claude-Code-Prompt (für dieses Dokument)

```
Lies docs/00-architecture.md und docs/01-github-issues.md. Erzeuge scripts/bootstrap_github.sh
exakt nach §6, ergänze die fehlenden Task-Issues aus §4 nach dem mk-Muster, und führe das Skript
aus, um Labels, Milestones (M0–M6), Epics (E1–E14) und alle Task-Issues anzulegen. Aktualisiere
danach jede Epic-Beschreibung mit einer Checkliste ihrer Task-Issues. Beginne noch keinen
Anwendungscode — committe nur das Bootstrap-Skript.
```
