## Ziel

Das Python-Backend unter `apps/api/` ist ein vollständiges `uv`-Projekt: `pyproject.toml` mit den vorgegebenen Runtime- und Dev-Dependencies, `uv sync` erzeugt `.venv` + `uv.lock`, und `uv run` funktioniert. **`pip` wird nirgends verwendet.**

## Kontext & Prinzipien

- **P9 (`uv` ausschließlich):** Dies ist der definierende Task für P9. Jede Dependency-Änderung erfolgt über `uv add` / `uv add --dev`; `uv.lock` wird committet, damit CI (FND-6) reproduzierbar dieselben Versionen baut. Ein einziger `pip install` würde gegen P9 und die DoD verstoßen.
- **P2 (kuratierte Bewertung):** `sympy` ist bereits als Dependency vorgesehen, weil der spätere Math-Grader symbolisch/numerisch (nicht per LLM) prüft — die Wahl der Lib gehört in das Foundations-Setup.
- **P3/P5 (interpretierbares Learner-Modell):** `numpy` für BKT ist vorgesehen; kein ML-Framework, das ein Blackbox-Modell nahelegen würde.

## Zu erstellende/ändernde Dateien

```
apps/api/pyproject.toml
apps/api/uv.lock                       # von `uv sync` erzeugt, committen
apps/api/src/its/__init__.py           # Paketmarker
apps/api/src/its/api/__init__.py       # Paketmarker (für spätere student.py/teacher.py)
```

> Hinweis: zu entscheiden — Build-Backend für das `src/`-Layout. `docs/02` gibt kein `[build-system]` an. Empfehlung: Hatchling mit explizitem `packages = ["src/its"]`, damit `import its` und `its.main:app` aufgelöst werden. (Siehe Open Questions des Epics.)

## Schnittstellen & Signaturen

`apps/api/pyproject.toml` (exakt aus `docs/02` Section 2):

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

Referenz-Befehle (aus `docs/02` Section 2):

```bash
cd apps/api
uv sync                      # erstellt .venv + uv.lock
uv run uvicorn its.main:app --reload
uv run pytest
```

> **Regel:** Niemals `pip install`. Neue Dependency = `uv add <pkg>` (bzw. `uv add --dev`).

## Umsetzungsschritte

- [ ] `apps/api/pyproject.toml` exakt mit obigem Inhalt anlegen.
- [ ] Build-Backend ergänzen (Empfehlung Hatchling): `[build-system]` mit `requires = ["hatchling"]`, `build-backend = "hatchling.build"`, plus `[tool.hatch.build.targets.wheel] packages = ["src/its"]`.
- [ ] `apps/api/src/its/__init__.py` und `apps/api/src/its/api/__init__.py` als leere Paketdateien anlegen.
- [ ] `uv sync` in `apps/api/` ausführen → erzeugt `.venv/` (ignoriert) und `uv.lock`.
- [ ] `uv.lock` committen.
- [ ] Smoke-Import prüfen: `uv run python -c "import its; print('ok')"`.
- [ ] Sicherstellen, dass kein `requirements.txt`/`pip`-Aufruf existiert.

## Akzeptanzkriterien

- [ ] `uv sync` läuft fehlerfrei und erzeugt `.venv` + `uv.lock`.
- [ ] `uv run python -c "import its"` ist erfolgreich (src-Layout korrekt aufgelöst).
- [ ] `pyproject.toml` enthält genau die vorgegebenen Runtime- und Dev-Dependencies sowie den `[tool.ruff]`-Block.
- [ ] `uv.lock` ist versioniert.
- [ ] Keine `pip`-Nutzung und kein `requirements.txt` im Repo.

## Tests / Verifikation

```bash
cd apps/api
uv sync
uv run python -c "import its; print('import ok')"   # erwartet: import ok
uv run python -c "import fastapi, sqlalchemy, pgvector, sympy, numpy; print('deps ok')"
ls .venv && test -f uv.lock && echo "lock present"
```
Erwartet: alle Importe erfolgreich; `uv.lock` vorhanden; `.venv/` existiert (aber ignoriert).

## Abhängigkeiten

- **Abhängig von:** FND-1 — der Verzeichnisbaum `apps/api/` muss existieren, bevor das `uv`-Projekt darin angelegt wird.
- **Nachgelagert:** FND-4 (importiert `fastapi`/`pydantic-settings`), FND-5 (importiert `python-jose` später), FND-6 (CI ruft `uv sync && uv run pytest`).

## Definition of Done

- [ ] Akzeptanzkriterien dieses Tasks erfüllt.
- [ ] Tests/Verifikation grün (Importe, Lockfile vorhanden).
- [ ] **`uv`-only, keine `pip`-Aufrufe** (DoD-blockierend, P9).
- [ ] Keine PII/Secrets im `pyproject.toml`/`uv.lock`.
- [ ] GitHub-Issue FND-2 geschlossen, E1-Epic-Checkliste aktualisiert.
