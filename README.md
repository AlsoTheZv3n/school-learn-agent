# EduSovereign — Intelligent Tutoring System (ITS)

Ein datenschutzkonformes Intelligent Tutoring System für Schulen: Lernmaterial pro
Stufe/Fach, ein individueller, **inspizierbarer** Lernstand pro Schüler:in, ein
pädagogischer Agent, der erklärt und abfragt — und eine Lehrer:innen-Ansicht zur
Kontrolle und Intervention. Gebaut für **Minderjährige**, deshalb Safety und
Datenresidenz (CH/EU) als Voraussetzung, nicht als Zusatz.

Status: **vollständig implementiert** (Backend + Frontend), getestet (59+ Tests,
CI-grün). Auth, das echte LLM und der Embedder sind bewusst noch Stubs — siehe
[Pre-Prod-Gates](#pre-prod-gates).

---

## Architektur

```
                 Schüler:in                    Lehrperson
                     ↕                              ↕
            Pädagogischer Agent  ⇄  Open Learner Model + Dashboard
              (LangGraph-Loop)            (Mastery + Unsicherheit)
                     ↓ fragt Wissen ab
              Retrieval-Router
            ┌────────┼────────┐
        Semantic  Individual  Population
       (geteilt) (1 Schüler)  (Kohorte ≥ k)
            └────────┼────────┘
        ╔════════════▼════════════╗
        ║   Safety & Isolation    ║  Row-Level Security · Min-Cohort-Schwelle
        ╚════════════▼════════════╝
              ein PostgreSQL + pgvector
```

### Nicht verhandelbare Prinzipien
- **P1 — Safety in der DB:** Isolation per **Row-Level Security**, nicht per App-`if`.
- **P2 — Kuratierte Bewertung:** `assess` prüft gegen einen kuratierten Answer-Key
  (symbolisch via `sympy`), **nicht** per LLM. Generative Freiheit nur beim Erklären.
- **P3 — Das Modell verbessert sich, nicht der Agent:** ein interpretierbares
  **Bayesian Knowledge Tracing** (BKT) pro Skill; Agentverhalten ist Funktion davon.
- **P4 — PII verlässt die Maschine nicht:** Anonymisierung vor jedem externen LLM-Call.
- **P5 — Open Learner Model:** Lehrer-Sicht zeigt Mastery **inkl. Unsicherheit**;
  Schüler-Sicht nie die Rohschätzung.
- **P6 — Mensch im Loop:** Lehrperson kann verifizieren, überschreiben, Notizen geben.
- **P7 — Genau eine Plugin-Naht:** fachspezifische Bewertung (`grading/`).
- **P8 — Datenresidenz CH/EU** · **P9 — `uv` ausschliesslich (kein `pip`).**

---

## Tech-Stack

| Teil | Wahl |
|---|---|
| Datenbank (Vektor + relational + Aggregate) | **ein** PostgreSQL + `pgvector` |
| Isolation | Postgres **Row-Level Security** + Min-Cohort-Check |
| Agent / Retrieval-Router | **LangGraph** |
| Lernmodell | **BKT** (interpretierbar; DKT als späterer Swap) |
| Bewertung | `GraderStrategy`-Registry (Math symbolisch via `sympy`) |
| LLM / Embeddings | Backend umschaltbar (`local` Stub · `frontier`), anonymisiert |
| Backend | **FastAPI** + Pydantic (Python ≥ 3.12, `uv`) |
| Frontend | **React + TypeScript + Vite + Tailwind** (Design „EduSovereign") |
| Auth | Rollen student/teacher/admin (JWT-Stub; IdP folgt) |

---

## Repository-Layout

```
apps/
  api/                 # FastAPI-Backend (uv)
    src/its/
      db/              # SQLAlchemy-Modelle, Session (RLS-Hook), Alembic-Migrationen
      safety/          # rls.sql, scoping.py, cohort.py   ← das Isolations-Gate
      retrieval/       # router + semantic/individual/population + graph (CTE)
      content/         # parser, ingest, kuratierte Items
      learner_model/   # bkt.py, tracing.py, dkt.py (Stub)
      grading/         # base + registry + math/language/history (Plugin-Naht)
      agent/           # LangGraph: state.py, graph.py, nodes/   ← der Agent
      llm/             # client.py, anonymize.py, embeddings.py, prompts/
      api/             # student.py, teacher.py, content.py, dev.py, errors.py
  web/                 # React/TS-Frontend (Vite + Tailwind)
content/               # kuratierter Markdown-Vault (Demo)
infra/                 # docker-compose (Postgres + pgvector)
scripts/               # seed.py, import_production.py, GitHub-Bootstrap
tests/                 # pytest (inkl. CI-blockierende Safety-Tests)
```

---

## Lokal starten (3 Teile)

> Voraussetzungen: Docker, [`uv`](https://docs.astral.sh/uv/), Node ≥ 20.
> Die Ports (DB 5433, API 8010, Web 5181) sind so gewählt, dass sie nicht mit anderen
> lokalen Diensten kollidieren — anpassbar in `infra/docker-compose.yml` und
> `apps/web/vite.config.ts`.

**1) Datenbank**
```bash
docker compose -f infra/docker-compose.yml up -d   # Postgres + pgvector auf 127.0.0.1:5433
```

**2) Backend** (aus `apps/api/`)
```bash
# Umgebung (PowerShell-Beispiel)
$env:DATABASE_URL = "postgresql+psycopg://its:its_dev_pw@127.0.0.1:5433/its"
$env:DATA_MODE = "mock"; $env:AUTH_DEV_MODE = "1"

uv sync
uv run alembic upgrade head                         # Schema + RLS + Seed
uv run python ../../scripts/seed.py --profile demo  # 1 Klasse, 25 Schüler:innen, 1 Lehrperson
uv run uvicorn its.main:app --host 127.0.0.1 --port 8010
```

**3) Frontend** (aus `apps/web/`)
```bash
npm install
npm run dev          # → http://localhost:5181  (proxyt /student,/teacher,… an :8010)
```

Im Browser oben rechts **„Lehrer-Ansicht"** bzw. in der Lehrer-Sidebar **„Schüler-Ansicht"**
wechselt die Rolle. In der Lernsession eine Aufgabe beantworten → kuratierte Bewertung +
Mastery-Update; im Lehrer-Dashboard auf „Details" → Open Learner Model mit Unsicherheit.

---

## Der Agent

Der pädagogische Agent ist eine **LangGraph-State-Machine** unter `apps/api/src/its/agent/`:

```
route → retrieve → (intent=answer? → assess → update_model | sonst → explain) → END
```

- `assess` bewertet mit dem **kuratierten** Grader (P2), `update_model` schreibt das
  Ergebnis via **BKT** ins Learner-Modell (P3), `explain` ist der einzige generative Pfad.
- Ausgelöst über `POST /student/turn` (`api/student.py`), sichtbar in der **Lernsession**.

---

## Tests & CI

```bash
cd apps/api && uv run pytest          # alle Tests (Safety-Tests gegen echtes Postgres)
cd apps/web && npm run build          # tsc-Typecheck + Vite-Build
```

GitHub Actions (`.github/workflows/ci.yml`) hat zwei Jobs: **`test`** (pytest mit
vorgelagertem, blockierendem Safety-Gate) und **`web`** (Frontend-Build).

---

## Pre-Prod-Gates

Bewusst vereinfacht — **vor echtem Schülerdaten-Betrieb zu ersetzen**:
1. **Auth:** `current_principal` ist ein Stub. Für lokales Testen akzeptiert er
   `dev:<role>:<user>[:<student>]`-Tokens, wenn `AUTH_DEV_MODE=1`. → echtes JWT/IdP.
2. **LLM:** `llm/client.py` lokaler Backend = deterministischer Stub. → lokales Modell
   (Qwen2.5) **oder** Frontier-API mit AVV/No-Training (Anonymisierung steht bereits).
3. **Embedder:** `HashingEmbedder`-Stub. → echtes Embedding-Modell.

---

## Compliance-Hinweis

Diese Plattform verarbeitet identifizierbare Daten über **Minderjährige**. Datenresidenz
(CH/EU, revDSG/DSGVO), PII-Minimierung im LLM-Pfad und die Isolationsgarantien sind
**keine optionalen Features**, sondern Voraussetzung. Vor Produktivbetrieb mit echten
Schülerdaten ist eine fachliche/rechtliche Prüfung gegen aktuelle Quellen erforderlich.

> Die ausführliche Planung, die Fachspezifikationen, der Sicherheits-Audit und die
> Compliance-Details liegen lokal unter `docs/` (nicht im Repository versioniert).
