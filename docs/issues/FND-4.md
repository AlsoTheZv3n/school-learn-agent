## Ziel

Ein minimales **FastAPI-Skeleton** läuft: `uv run uvicorn its.main:app` startet die App, und `GET /health` liefert `{"status":"ok"}`. Konfiguration wird typisiert über `pydantic-settings` aus `.env` geladen.

## Kontext & Prinzipien

- **Tech-Stack (FastAPI + Pydantic):** Pydantic validiert später Query-Parameter für sichere Templates (relevant für Retrieval/Safety). Hier wird die Settings-Basis gelegt — typisierte Konfiguration statt verstreuter `os.getenv`-Aufrufe.
- **P1 (Safety):** `min_cohort_k` und `database_url` sind bereits Teil der Settings, weil die spätere Safety-Schicht (RLS/Min-Cohort) zentral auf `settings` zugreift — der Default `k=10` lebt von Anfang an hier.
- **P4/P8 (PII/Residenz):** `llm_backend`/`llm_api_key` sind in den Settings vorgesehen, damit der spätere LLM-Pfad seinen Inferenzort (lokal vs. frontier) kontrolliert ableiten kann.

## Zu erstellende/ändernde Dateien

```
apps/api/src/its/config.py
apps/api/src/its/main.py
tests/test_health.py            # erster Test (gibt CI etwas zum Ausführen)
```

## Schnittstellen & Signaturen

`apps/api/src/its/config.py` (aus `docs/02` Section 4):

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

`apps/api/src/its/main.py` (aus `docs/02` Section 4):

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

## Umsetzungsschritte

- [ ] `apps/api/src/its/config.py` mit obigem Inhalt anlegen.
- [ ] `apps/api/src/its/main.py` mit `create_app()`-Factory und Modulvariable `app` anlegen.
- [ ] `tests/test_health.py` schreiben, das mit FastAPI `TestClient` (httpx-basiert) `GET /health` aufruft und `200` + `{"status":"ok"}` prüft.
- [ ] Lokal eine `.env` aus `.env.example` ableiten (mind. `DATABASE_URL` setzen), damit `Settings()` instanziierbar ist.
- [ ] Server lokal starten und `/health` per `curl` prüfen.

> Hinweis: `Settings()` erfordert `database_url`. Für den reinen Health-Test ohne `.env` kann der Test `DATABASE_URL` per Monkeypatch/Env setzen, damit `config.py` importierbar bleibt — zu entscheiden, ob `main.py` `settings` überhaupt importiert (aktuell nicht nötig für `/health`).

## Akzeptanzkriterien

- [ ] `uv run uvicorn its.main:app` startet ohne Fehler.
- [ ] `GET /health` antwortet mit Status `200` und Body `{"status":"ok"}`.
- [ ] `Settings` lädt `database_url` (Pflicht) und die Defaults (`data_mode=mock`, `min_cohort_k=10`, `llm_backend=local`).
- [ ] `create_app()` ist eine Factory; `app` ist als Modulvariable für `uvicorn its.main:app` verfügbar.
- [ ] `tests/test_health.py` ist grün.

## Tests / Verifikation

```bash
cd apps/api
uv run pytest -q ../../tests/test_health.py        # erwartet: 1 passed
# Manuell:
uv run uvicorn its.main:app &
curl -s http://127.0.0.1:8000/health               # erwartet: {"status":"ok"}
```
Erwartet: pytest grün; `curl` liefert exakt `{"status":"ok"}` mit HTTP 200.

## Abhängigkeiten

- **Abhängig von:** FND-2 — `fastapi`, `pydantic-settings` und das importierbare `its`-Paket müssen via `uv sync` vorhanden sein.
- **Nachgelagert:** FND-5 (mountet später Auth-Dependencies in dieselbe App), FND-6 (CI führt `tests/test_health.py` aus), E-spätere API-Tasks (`its.api.student`/`its.api.teacher`).

## Definition of Done

- [ ] Akzeptanzkriterien dieses Tasks erfüllt.
- [ ] Tests grün (`tests/test_health.py`).
- [ ] Kein LLM-Pfad in diesem Task → keine PII-Sorge, aber `llm_api_key` bleibt None/leer.
- [ ] `uv`-only (Start/Tests via `uv run`, kein `pip`).
- [ ] GitHub-Issue FND-4 geschlossen, E1-Epic-Checkliste aktualisiert.
