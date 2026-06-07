## Ziel

Das Monorepo `its-platform/` existiert mit dem in der Architektur vorgegebenen Verzeichnisbaum sowie versionierten Root-Dateien (`.gitignore`, `.editorconfig`, `README.md`). Damit gibt es eine konsistente Wurzel, in die alle weiteren Tasks (uv-Projekt, Infra, API, CI) ihre Dateien legen.

## Kontext & Prinzipien

- **P9 (`uv` ausschließlich):** Der Baum trennt `apps/api/` (Python-Backend, später `uv`-verwaltet) klar von `apps/web/` (Frontend) — keine Vermischung von Toolchains. `.gitignore` schließt `.venv/` ein, damit nie ein virtuelles Environment eincheckt wird.
- **P8 (Datenresidenz/PII):** `.gitignore` muss `.env` ausschließen (aber `.env.example` zulassen), damit keine Secrets/PII-Konfiguration ins Repo gelangt.
- **P7 (genau eine Plugin-Naht):** Der Baum spiegelt die bewusste Asymmetrie wider — nur `grading/` wird später eine Registry; alle anderen Module sind flach. In FND-1 wird die Struktur lediglich vorbereitet (leere Verzeichnisse), nicht implementiert.

## Zu erstellende/ändernde Dateien

```
its-platform/
├── apps/
│   ├── api/                 # (Inhalt in FND-2/4/5)
│   └── web/                 # React + TS (späteres Epic) — Platzhalter
├── content/
│   └── math/                # kuratierter Markdown-Vault (späteres Epic) — Platzhalter
├── infra/                   # (docker-compose in FND-3)
├── scripts/                 # Hilfsskripte — Platzhalter
├── tests/                   # (Tests ab FND-4)
├── .editorconfig
├── .gitignore
└── README.md
```

> Hinweis: Leere Verzeichnisse werden von Git nicht versioniert. Lege in `apps/web/`, `content/math/`, `scripts/`, `infra/` und `tests/` je eine `.gitkeep` an, bis echte Dateien folgen.

## Schnittstellen & Signaturen

`.gitignore` deckt mindestens ab (aus `docs/02` Section 1):

```gitignore
__pycache__/
.venv/
*.pyc
node_modules/
dist/
.env
.pytest_cache/
*.egg-info/
```

`.editorconfig` (an bestehender Root-Konvention orientiert):

```ini
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 2

[*.py]
indent_size = 4
max_line_length = 100

[*.md]
trim_trailing_whitespace = false
```

## Umsetzungsschritte

- [ ] Verzeichnisse anlegen: `apps/api/`, `apps/web/`, `content/math/`, `infra/`, `scripts/`, `tests/`.
- [ ] In jedes (vorerst leere) Verzeichnis eine `.gitkeep` legen (`apps/web/`, `content/math/`, `infra/`, `scripts/`, `tests/`).
- [ ] `.gitignore` anlegen/prüfen, sodass mindestens die oben genannten Einträge enthalten sind (vorhandene Root-Datei abgleichen, fehlende Einträge `node_modules/`, `dist/` ergänzen).
- [ ] `.editorconfig` anlegen/prüfen (siehe Snippet).
- [ ] `README.md` mit Quickstart-Abschnitt schreiben: (1) `docker compose -f infra/docker-compose.yml up -d`, (2) `cd apps/api && uv sync`, (3) `uv run uvicorn its.main:app --reload`, (4) `curl http://127.0.0.1:8000/health`.
- [ ] Verifizieren, dass `git status` alle Verzeichnisse erfasst (dank `.gitkeep`).

## Akzeptanzkriterien

- [ ] Verzeichnisbaum entspricht `docs/00` Section 6 / `docs/02` Section 1 (`apps/api`, `apps/web`, `content/math`, `infra`, `scripts`, `tests`).
- [ ] `.gitignore` schließt mindestens `__pycache__/`, `.venv/`, `*.pyc`, `node_modules/`, `dist/`, `.env`, `.pytest_cache/`, `*.egg-info/` ein und lässt `.env.example` zu.
- [ ] `.editorconfig` vorhanden (4-Space für `.py`, 2-Space sonst, `max_line_length=100` für Python).
- [ ] `README.md` enthält einen lauffähigen Quickstart.
- [ ] Alle leeren Verzeichnisse sind via `.gitkeep` versioniert.

## Tests / Verifikation

```bash
# Baum prüfen
ls -la its-platform/apps its-platform/content its-platform/infra its-platform/scripts its-platform/tests
# .gitignore-Einträge prüfen
git -C its-platform check-ignore -v .venv/ .env || true   # sollte als ignoriert gemeldet werden
git -C its-platform check-ignore .env.example && echo "FEHLER: .env.example ignoriert" || echo "ok: .env.example versionierbar"
# Versionierung prüfen
git -C its-platform status --porcelain
```
Erwartet: alle Zielverzeichnisse existieren; `.venv/`/`.env` werden ignoriert; `.env.example` ist nicht ignoriert; `.gitkeep`-Dateien erscheinen als neu zu committen.

## Abhängigkeiten

- Keine Vorabhängigkeit (Projektstart).
- **Nachgelagert:** FND-2 (legt `apps/api/pyproject.toml` in den hier geschaffenen Baum), FND-3 (`infra/`), FND-4/FND-5 (`apps/api/src/its/...`), FND-6 (`.github/workflows/`). Alle setzen die Verzeichnisstruktur dieses Tasks voraus.

## Definition of Done

- [ ] Akzeptanzkriterien dieses Tasks erfüllt.
- [ ] Tests/Verifikation oben ausgeführt, Ergebnisse wie erwartet.
- [ ] Keine PII/Secrets versioniert (`.env` ignoriert, nur `.env.example` zugelassen).
- [ ] `uv`-only-Konvention vorbereitet (`.venv/` ignoriert); keine `pip`-Artefakte.
- [ ] GitHub-Issue FND-1 geschlossen, E1-Epic-Checkliste aktualisiert.
