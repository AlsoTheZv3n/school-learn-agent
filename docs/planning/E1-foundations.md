# E1 — Foundations: Monorepo, Infra, Skeleton — Detailplanung

> Milestone: **M0 Foundations** · Quelle: `docs/02-foundations.md` · maßgebliche Prinzipien: `docs/00-architecture.md` (P1–P9, Section 6 Repository-Layout, Section 8 DoD)

## 1. Scope & Zielbild

Ziel von E1 ist ein **lauffähiges, leeres Grundgerüst**, auf dem alle späteren Epics (E2 DB, E3 Safety/RLS, E4 Retrieval, …) aufsetzen können — ohne dass in E1 schon fachliche Logik (Tracing, Grading, Retrieval) entsteht. Konkret am Ende von E1:

- Monorepo `its-platform/` mit dem in `docs/00` Section 6 vorgegebenen Layout (`apps/api`, `apps/web`, `content/`, `infra/`, `scripts/`, `tests/`).
- Python-Backend ausschließlich über **`uv`** verwaltet (P9), reproduzierbarer `uv.lock`, **kein `pip`**.
- **Postgres 16 + pgvector** lokal via Docker-Compose, mit aktivierter `vector`- und `uuid-ossp`-Extension.
- **FastAPI-Skeleton** mit `create_app()`-Factory und `GET /health` → `{"status":"ok"}`.
- **Auth-Rollen-Gerüst**: `Role`-Enum (student/teacher/admin), `Principal`, `current_principal`-Dependency (bewusst noch Stub), `PG_ROLE`-Mapping — exakt die Rollen, auf die später RLS keyt (P1/P5/P6).
- **CI** (GitHub Actions), die einen Postgres-Service hochfährt, die Extension anlegt und `uv run pytest` ausführt; rote Tests **blockieren** den Merge.

Was E1 **nicht** umfasst (Abgrenzung, um Scope-Creep zu vermeiden):
- Keine ORM-Modelle/Tabellen (das ist E2/DB, `docs/03`).
- Keine RLS-Policies/`rls.sql` (das ist E3/Safety, `docs/04`) — E1 legt nur das **Rollen-Namens-Mapping** an, das E3 voraussetzt.
- Kein echtes JWT-Decoding (FND-5 liefert bewusst einen markierten Stub).
- Kein Frontend-Code in `apps/web/` außer einem Platzhalter, der die Verzeichnisexistenz sichert.

## 2. Task-Reihenfolge & Abhängigkeiten

```
FND-1 (Monorepo-Skelett)
  ├─> FND-2 (uv-Projekt) ──┬─> FND-4 (FastAPI /health) ──> FND-5 (Auth-Rollen-Gerüst)
  │                        │
  │                        └─> FND-6 (CI)  <── benötigt auch FND-3
  └─> FND-3 (Docker-Compose Postgres+pgvector) ──> FND-6 (CI)
```

Empfohlene Bearbeitungsreihenfolge (kritischer Pfad zuerst):
1. **FND-1** — Verzeichnisbaum + `.gitignore`/`.editorconfig`/`README` (Wurzel für alles).
2. **FND-2** — `pyproject.toml` + `uv sync` (entsperrt FND-4 und FND-6).
3. **FND-3** — Docker-Compose (parallel zu FND-2 möglich; entsperrt FND-6).
4. **FND-4** — `config.py` + `main.py` mit `/health` (braucht FND-2).
5. **FND-5** — `auth/roles.py` + `auth/deps.py` (braucht FND-4).
6. **FND-6** — `ci.yml` (braucht FND-2 für `uv`-Lauf und FND-3-Image für den Service).

Nachgelagert (außerhalb E1, hängen an E1-Ergebnissen):
- **E2/DB** (`docs/03`) baut auf `apps/api/src/its/db/` und dem `DATABASE_URL` aus `.env.example`.
- **E3/Safety** (`docs/04`) baut auf dem `PG_ROLE`-Mapping (FND-5) und dem laufenden Postgres (FND-3) auf; die CI-blockierenden Safety-Tests laufen im FND-6-Workflow.

## 3. Feinere Sub-Task-Zerlegung (über die Issues hinaus)

**FND-1**
- Verzeichnisse anlegen, leere Verzeichnisse mit `.gitkeep` versionierbar machen (`apps/web/`, `content/math/`, `infra/`, `scripts/`, `tests/`).
- `.gitignore` und `.editorconfig` aus dem Repo-Root übernehmen/prüfen (existieren bereits — Inhalt gegen `docs/02` Section 1 abgleichen, ggf. ergänzen `dist/`, `node_modules/`).
- `README.md` mit Quickstart-Block (Docker up, `uv sync`, `uvicorn`, curl /health).

**FND-2**
- `apps/api/src/its/__init__.py` und `apps/api/src/its/api/__init__.py` als Pakete anlegen (sonst findet `its.main:app` das Paket nicht).
- `[tool.hatch]`/`[build-system]`-Entscheidung: src-Layout muss vom Build-Backend gefunden werden (siehe Designentscheidung 4.1).
- `uv sync` ausführen, `uv.lock` committen.
- Smoke: `uv run python -c "import its"`.

**FND-3**
- `infra/init/01-extensions.sql` anlegen (wird nur beim **ersten** Container-Start mit leerem Volume ausgeführt).
- `.env.example` im Repo-Root anlegen (nicht in `infra/`).
- Healthcheck verifizieren (`docker compose ps` zeigt `healthy`).

**FND-4**
- `config.py` mit `pydantic-settings`; `settings = Settings()` mit `# type: ignore[call-arg]`.
- `main.py` mit `create_app()`-Factory + Modulvariable `app`.
- Erster Test `tests/test_health.py` mit `httpx`/`TestClient` (gibt FND-6 sofort etwas zum Ausführen).

**FND-5**
- `auth/__init__.py` anlegen.
- `roles.py` (StrEnum + `PG_ROLE`), `deps.py` (`Principal`, `current_principal`-Stub).
- Test, der bei fehlendem `Authorization`-Header `401` und sonst `NotImplementedError` belegt (dokumentiert den Stub-Vertrag).

**FND-6**
- `setup-uv`-Action, Caching optional.
- Schritt „Enable extensions" gegen den Service-Postgres.
- `working-directory: apps/api` für `uv sync && uv run pytest`.
- Sicherstellen, dass mind. ein Test existiert (sonst `pytest`-Exit-Code 5 „no tests collected" → CI je nach Konfiguration grün-fälschlich oder rot).

## 4. Zentrale Designentscheidungen mit Begründung

**4.1 src-Layout + Build-Backend.** `docs/02` zeigt `apps/api/src/its/...` und `its.main:app`. Damit `uv`/das Build-Backend das Paket unter `src/` findet, braucht `pyproject.toml` eine passende Build-Konfiguration (z. B. Hatchling mit `packages = ["src/its"]`). Das Doc spezifiziert das Build-Backend nicht — siehe Open Question. Empfehlung: Hatchling mit explizitem `tool.hatch.build.targets.wheel.packages`.

**4.2 `uv` ausschließlich (P9).** Jede Dependency-Operation über `uv add` / `uv sync`; `uv.lock` wird committet für reproduzierbare CI. `pip` taucht nirgends auf — auch nicht in der CI. Das ist DoD-blockierend (`docs/00` Section 8).

**4.3 Auth bewusst als Stub (FND-5).** Echtes JWT-Decoding gehört nicht in M0; der Stub wirft `NotImplementedError` mit klarer TODO-Markierung. Wichtig ist nur, dass `Role`/`Principal`/`PG_ROLE` schon **genau die Rollen** definieren, auf die E3-RLS keyt (`its_student/its_teacher/its_admin`) — sonst müsste E3 das Mapping nachträglich brechen. Bezug: P1 (RLS keyt auf Rollen), P6 (Lehrer-Rolle ist Sicherheitsarchitektur).

**4.4 init-SQL statt App-Migration für Extensions.** Die Extensions (`vector`, `uuid-ossp`) werden über `docker-entrypoint-initdb.d` beim ersten Start gesetzt; in CI separat per `psql`, weil der GitHub-Actions-Service kein init-Volume mountet. Das hält die spätere Alembic-Migration (E2/E3) frei von Extension-Bootstrapping.

**4.5 `.env.example` im Repo-Root.** `docs/02` Section 3 verortet `.env.example` im Root (nicht `infra/`); `config.py` liest `.env` (relativ zum Arbeitsverzeichnis von `uvicorn`). Hinweis für spätere Tasks: Arbeitsverzeichnis-Konvention dokumentieren.

**4.6 Keine RLS in E1.** P1 verlangt RLS „früh" (M1), nicht in M0. E1 schafft nur die Voraussetzung (Rollennamen). Das verhindert, dass Features auf RLS aufsetzen, bevor sie existiert — und hält M0 klein.

## 5. Risiken & Gegenmaßnahmen

- **Paket nicht importierbar (src-Layout).** Falsches/fehlendes Build-Backend → `uv run uvicorn its.main:app` schlägt fehl. → Gegenmaßnahme: Build-Backend explizit konfigurieren, Smoke-Test `uv run python -c "import its"` in FND-2.
- **CI „no tests collected" (Exit 5).** Wenn FND-6 vor FND-4 läuft und kein Test existiert, ist das Signal mehrdeutig. → Mindestens `tests/test_health.py` als Teil von FND-4 anlegen, bevor CI scharf geschaltet wird.
- **pgvector-Extension fehlt in CI.** Der Service-Container führt `init/`-Skripte nicht aus. → Expliziter `psql ... CREATE EXTENSION`-Schritt (bereits im Doc) verifizieren; Verbindung erst nach Healthcheck.
- **Schleichende `pip`-Nutzung.** Verstößt gegen P9/DoD. → CI nutzt nur `uv`; optional ein Lint/Grep-Gate gegen `pip install` in Skripten.
- **PII/Datenresidenz schon in M0 relevant (P4/P8).** `.env.example` enthält `LLM_API_KEY`/`LLM_BACKEND=local`. → Default `local` belassen; keine echten Keys committen (`.env` ist ignoriert); CH/EU-Hosting als spätere Infra-Entscheidung markieren.

## 6. Offene Fragen / zu treffende Entscheidungen

- Build-Backend für das src-Layout (Hatchling vs. setuptools) — `pyproject.toml` im Doc hat kein `[build-system]`.
- Python-Version exakt: `requires-python = ">=3.12"` vs. gepinnte `3.12.x` über `.python-version` für reproduzierbare CI.
- `pytest-asyncio`-Modus (`asyncio_mode = "auto"` vs. explizite Marker) — relevant, sobald async-Tests kommen.
- IdP-Wahl und JWT-Claims-Mapping (FND-5 ist Stub): welcher Claim trägt `role`, welcher die `student_id`? Welcher Public-Key-Bezug (`JWT_PUBLIC_KEY`)?
- Frontend-Bootstrapping-Zeitpunkt: bleibt `apps/web/` in M0 ein `.gitkeep`-Platzhalter oder schon Vite-Init?
- Soll die CI bereits einen `ruff`-Lint-Schritt enthalten oder erst später?

(Details inkl. Empfehlung in `open_questions`.)

## 7. Test-/Verifikationsstrategie für das Epic

**Lokal (Definition-of-Done-Beweis):**
1. `docker compose -f infra/docker-compose.yml up -d` → `docker compose -f infra/docker-compose.yml ps` zeigt Service `db` als `healthy`.
2. `docker compose -f infra/docker-compose.yml exec db psql -U its -d its -c "SELECT extname FROM pg_extension;"` → enthält `vector` und `uuid-ossp`.
3. In `apps/api`: `uv sync` (legt `.venv` + `uv.lock` an, kein `pip`).
4. `uv run uvicorn its.main:app` startet ohne Fehler; in zweitem Terminal `curl http://127.0.0.1:8000/health` → `{"status":"ok"}`.
5. `uv run pytest -q` → grün (mind. Health-Test + Auth-Stub-Test).

**CI:** Push/PR triggert `ci.yml`; Postgres-Service wird `healthy`, Extension angelegt, `uv run pytest -q` grün. Ein absichtlich rot gesetzter Test muss den Job rot machen (Merge-Blocker verifizieren).

**Smoke-Eigenschaften:** `import its` funktioniert; `from its.auth.roles import Role, PG_ROLE` und `from its.auth.deps import Principal, current_principal` importierbar.
