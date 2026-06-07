# 02 — Foundations (E1, M0)

**Ziel:** Lauffähiges Grundgerüst — Monorepo, `uv`-Projekt, Postgres+pgvector via Docker,
FastAPI-Skeleton mit Healthcheck, Auth-Rollen-Gerüst, CI.

**Voraussetzungen:** keine (Start).
**Issues:** FND-1 … FND-6.

---

## 1. Monorepo-Struktur (FND-1)

```
its-platform/
├── apps/
│   ├── api/
│   └── web/
├── content/
│   └── math/
├── infra/
├── scripts/
├── tests/
├── .editorconfig
├── .gitignore
└── README.md
```

`.gitignore` deckt mindestens ab: `__pycache__/`, `.venv/`, `*.pyc`, `node_modules/`,
`dist/`, `.env`, `.pytest_cache/`, `*.egg-info/`.

---

## 2. Python-Projekt mit `uv` (FND-2) — **kein `pip`**

`apps/api/pyproject.toml`:

```toml
[project]
name = "its-api"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.32",
  "sqlalchemy>=2.0",
  "alembic>=1.13",
  "psycopg[binary]>=3.2",
  "pgvector>=0.3",
  "pydantic>=2.9",
  "pydantic-settings>=2.5",
  "python-jose[cryptography]>=3.3",
  "langgraph>=0.2",
  "numpy>=2.1",
  "sympy>=1.13",
]

[dependency-groups]
dev = [
  "pytest>=8.3",
  "pytest-asyncio>=0.24",
  "httpx>=0.27",
  "ruff>=0.7",
]

[tool.ruff]
line-length = 100
target-version = "py312"
```

Befehle (Referenz):

```bash
cd apps/api
uv sync                      # erstellt .venv + uv.lock
uv run uvicorn its.main:app --reload
uv run pytest
```

> **Regel:** Niemals `pip install`. Neue Dependency = `uv add <pkg>` (bzw. `uv add --dev`).

---

## 3. Docker-Compose: Postgres + pgvector (FND-3)

`infra/docker-compose.yml`:

```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: its
      POSTGRES_PASSWORD: its_dev_pw
      POSTGRES_DB: its
    ports:
      - "5432:5432"
    volumes:
      - its_pgdata:/var/lib/postgresql/data
      - ./init:/docker-entrypoint-initdb.d:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U its -d its"]
      interval: 5s
      timeout: 5s
      retries: 10
volumes:
  its_pgdata:
```

`infra/init/01-extensions.sql` (beim ersten Start ausgeführt):

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

`.env.example` (Repo-Root):

```dotenv
DATABASE_URL=postgresql+psycopg://its:its_dev_pw@localhost:5432/its
DATA_MODE=mock          # mock | prod  (siehe docs/11)
MIN_COHORT_K=10
LLM_BACKEND=local       # local | frontier
LLM_API_KEY=
JWT_PUBLIC_KEY=
```

---

## 4. FastAPI-Skeleton (FND-4)

`apps/api/src/its/config.py`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    data_mode: str = "mock"
    min_cohort_k: int = 10
    llm_backend: str = "local"
    llm_api_key: str | None = None
    jwt_public_key: str | None = None

settings = Settings()  # type: ignore[call-arg]
```

`apps/api/src/its/main.py`:

```python
from fastapi import FastAPI

def create_app() -> FastAPI:
    app = FastAPI(title="ITS Platform API", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    # Router werden in späteren Paketen gemountet:
    # from its.api.student import router as student_router
    # from its.api.teacher import router as teacher_router
    # app.include_router(student_router); app.include_router(teacher_router)
    return app

app = create_app()
```

**AK:** `uv run uvicorn its.main:app` startet; `GET /health` liefert `{"status":"ok"}`.

---

## 5. Auth-Rollen-Gerüst (FND-5)

> Wichtig: Die Rollen sind exakt die, auf die später RLS keyt (siehe 04). Hier nur Gerüst.

`apps/api/src/its/auth/roles.py`:

```python
from enum import StrEnum

class Role(StrEnum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"

# Mapping App-Rolle -> Postgres-Rolle (für RLS, docs/04)
PG_ROLE = {
    Role.STUDENT: "its_student",
    Role.TEACHER: "its_teacher",
    Role.ADMIN: "its_admin",
}
```

`apps/api/src/its/auth/deps.py`:

```python
from dataclasses import dataclass
from fastapi import Depends, HTTPException, Header
from its.auth.roles import Role

@dataclass(frozen=True)
class Principal:
    user_id: str
    role: Role
    student_id: str | None = None   # gesetzt, wenn role == STUDENT

def current_principal(authorization: str | None = Header(default=None)) -> Principal:
    # TODO (FND-5): echtes JWT-Decoding gegen settings.jwt_public_key.
    # Vorerst Stub für lokale Entwicklung — MUSS vor Produktion ersetzt werden.
    if not authorization:
        raise HTTPException(status_code=401, detail="missing auth")
    raise NotImplementedError("JWT decoding to be implemented in FND-5")
```

**AK:** `Principal` + `current_principal`-Dependency vorhanden; dokumentierter Stub mit klarer
TODO-Markierung; `PG_ROLE`-Mapping definiert.

---

## 6. CI-Grundgerüst (FND-6)

`.github/workflows/ci.yml`:

```yaml
name: ci
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      db:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_USER: its
          POSTGRES_PASSWORD: its_dev_pw
          POSTGRES_DB: its
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U its -d its"
          --health-interval 5s --health-timeout 5s --health-retries 10
    env:
      DATABASE_URL: postgresql+psycopg://its:its_dev_pw@localhost:5432/its
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - name: Enable extensions
        run: |
          sudo apt-get update && sudo apt-get install -y postgresql-client
          psql "postgresql://its:its_dev_pw@localhost:5432/its" -c "CREATE EXTENSION IF NOT EXISTS vector;"
      - name: Test
        working-directory: apps/api
        run: |
          uv sync
          uv run pytest -q
```

**AK:** Workflow startet Postgres-Service, läuft `uv run pytest`, blockiert bei rot.

---

## 7. Akzeptanzkriterien (gesamt)

- [ ] Monorepo-Struktur vorhanden (FND-1)
- [ ] `uv sync` + `uv run` funktionieren; keine `pip`-Nutzung (FND-2)
- [ ] `docker compose up` startet Postgres mit `vector`-Extension (FND-3)
- [ ] `GET /health` → `{"status":"ok"}` (FND-4)
- [ ] `Role`, `Principal`, `current_principal`, `PG_ROLE` vorhanden (FND-5)
- [ ] CI läuft grün gegen Postgres-Service (FND-6)

---

## Claude-Code-Prompt

```
Setze E1 (docs/02-foundations.md) um: Monorepo-Struktur, uv-Projekt (pyproject.toml wie
angegeben, KEIN pip), infra/docker-compose.yml + init-SQL für pgvector, .env.example,
FastAPI-Skeleton mit /health, Auth-Rollen-Gerüst (roles.py/deps.py), und CI (ci.yml).
Verifiziere lokal: `docker compose -f infra/docker-compose.yml up -d`, dann in apps/api
`uv sync && uv run uvicorn its.main:app` und ein curl auf /health. Schliesse die Issues
FND-1..6 und hake sie in der E1-Checkliste ab.
```
