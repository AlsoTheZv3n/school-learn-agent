## Ziel

Eine **GitHub-Actions-CI** existiert, die bei jedem Push/PR einen Postgres-(pgvector-)Service hochfährt, die `vector`-Extension anlegt und im Backend `uv sync && uv run pytest` ausführt. Rote Tests **blockieren** den Merge.

## Kontext & Prinzipien

- **P9 (`uv` ausschließlich):** Die CI nutzt `astral-sh/setup-uv` und ausschließlich `uv`-Befehle — kein `pip` in der Pipeline. Das ist der maschinelle Wächter über P9/DoD.
- **P1 (Safety zuerst):** Der Workflow startet bewusst einen Postgres-Service, weil die später CI-blockierenden Safety-Tests (`test_rls.py`, `test_cohort_threshold.py`, `docs/04`/`docs/10`) eine echte DB brauchen. FND-6 legt die Infrastruktur dafür an, damit Safety-Regressionen den Merge stoppen können.
- **Reproduzierbarkeit:** Durch `uv.lock` (FND-2) baut die CI deterministisch dieselben Versionen wie lokal.

## Zu erstellende/ändernde Dateien

```
.github/workflows/ci.yml
```

## Schnittstellen & Signaturen

`.github/workflows/ci.yml` (aus `docs/02` Section 6):

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

## Umsetzungsschritte

- [ ] `.github/workflows/ci.yml` mit obigem Inhalt anlegen.
- [ ] Sicherstellen, dass mindestens ein Test existiert (`tests/test_health.py` aus FND-4 und/oder `tests/test_auth_stub.py` aus FND-5), damit `pytest` nicht mit „no tests collected" (Exit 5) endet.
- [ ] Prüfen, dass `pytest` aus `apps/api` heraus die `tests/`-Dateien im Repo-Root findet (ggf. `testpaths`/`rootdir` in `pyproject.toml` setzen, falls Tests nicht gefunden werden).
- [ ] Workflow durch einen Push/PR auslösen und den Lauf in GitHub Actions prüfen.
- [ ] Branch-Protection: `ci`-Check als Required Status setzen, damit rote Läufe den Merge blockieren.

> Hinweis: zu entscheiden — ob die CI bereits einen `ruff`-Lint-Schritt enthalten soll. `docs/02` zeigt nur `pytest`; `ruff` ist als Dev-Dependency vorhanden. Empfehlung: optionalen `uv run ruff check .`-Schritt ergänzen (nicht zwingend für die AK dieses Tasks).

## Akzeptanzkriterien

- [ ] Der Workflow startet den Postgres-Service (`pgvector/pgvector:pg16`) und wartet auf dessen Health.
- [ ] Der „Enable extensions"-Schritt legt die `vector`-Extension im Service-Postgres an.
- [ ] `uv sync` und `uv run pytest -q` laufen aus `apps/api/` und der Job ist grün.
- [ ] Ein absichtlich fehlschlagender Test macht den Job rot (Merge-Blocker).
- [ ] Es kommt kein `pip` in der Pipeline vor.

## Tests / Verifikation

```bash
# Lokale Vorab-Simulation des CI-Kerns:
docker compose -f infra/docker-compose.yml up -d
cd apps/api && uv sync && uv run pytest -q          # erwartet: passed
# In GitHub:
# 1) Push -> Actions-Tab zeigt Workflow 'ci' grün
# 2) Test mit `assert False` brechen, pushen -> 'ci' rot, Merge blockiert
```
Erwartet: lokal grün; CI grün bei intaktem Code, rot bei gebrochenem Test.

## Abhängigkeiten

- **Abhängig von:** FND-2 (CI ruft `uv sync && uv run pytest`; ohne `pyproject.toml`/`uv.lock` schlägt der Lauf fehl) und FND-3 (verwendet dasselbe `pgvector/pgvector:pg16`-Image als Service). Mindestens ein Test (FND-4/FND-5) sollte existieren, damit der Lauf aussagekräftig ist.
- **Nachgelagert:** E3/Safety (`docs/04`) — die CI-blockierenden Safety-Tests (`test_rls.py`, `test_cohort_threshold.py`) laufen in genau diesem Workflow gegen den Postgres-Service.

## Definition of Done

- [ ] Akzeptanzkriterien dieses Tasks erfüllt.
- [ ] CI läuft grün gegen den Postgres-Service und blockiert bei rot (mit Fehlschlag-Test verifiziert).
- [ ] **`uv`-only, keine `pip`-Aufrufe** in der Pipeline (DoD-blockierend, P9).
- [ ] Keine Secrets/PII im Workflow (nur Dev-Credentials für den ephemeren Service).
- [ ] GitHub-Issue FND-6 geschlossen, E1-Epic-Checkliste aktualisiert.
