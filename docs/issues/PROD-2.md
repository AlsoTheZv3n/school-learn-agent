## Ziel

Eine einzige Umgebungsvariable `DATA_MODE` (plus getrennte `DATABASE_URL`s) steuert, ob das System im Mock- oder Prod-Modus läuft. Guards werden **im Code** durchgesetzt: Seeder/Reset verweigern sich bei `DATA_MODE != mock`, der Produktions-Import verlangt `DATA_MODE == prod`, und Mock- und Echtdaten teilen niemals dieselbe Datenbank.

## Kontext & Prinzipien

- **P1 (Safety als Eigenschaft, nicht als Disziplin):** Wie RLS die Zeilenisolation in die DB verlagert, verlagert dieser Task die Mock/Prod-Trennung in code-seitig erzwungene Guards statt in Doku/Handarbeit. Eine versehentliche Datenvermischung soll strukturell unmöglich sein. Dieser Task ist `safety-critical`.
- **P8 (CH/EU-Residenz):** Getrennte `DATABASE_URL`s stellen sicher, dass die Prod-DB in der CH/EU-Region liegt (PROD-3) und nicht mit der lokalen Dev-DB verwechselt wird.
- **P9 (`uv`-only):** Tests/Skripte laufen über `uv run`.

## Zu erstellende/ändernde Dateien

- `scripts/seed.py` (bestehend, aus MOCK-1) — `_guard_not_prod()` nutzt `DATA_MODE`.
- `scripts/import_production.py` (bestehend, aus PROD-1) — `_require_prod()` nutzt `DATA_MODE`.
- `apps/api/src/its/config.py` (bestehend, aus FND-4) — `data_mode`/`database_url` sind bereits vorhanden; ggf. zentralen Guard-Helfer ergänzen.
- `.env.example` (Repo-Root, bestehend, aus FND-3) — dokumentiert Dev-Werte.
- `tests/test_guards.py` (neu) — beweist beide Guard-Richtungen.

## Schnittstellen & Signaturen

Modus-Toggle und getrennte DB-URLs (docs/11 B.2):

```dotenv
# .env (Dev)                         # .env (Prod, getrennt verwaltet)
DATA_MODE=mock                       DATA_MODE=prod
DATABASE_URL=...localhost...its      DATABASE_URL=...ch-region...its_prod
MIN_COHORT_K=10                      MIN_COHORT_K=10
```

Guard im Seeder/Reset (docs/11 A.1/A.3):

```python
def _guard_not_prod():
    if os.environ.get("DATA_MODE", "mock") != "mock":
        sys.exit("REFUSED: seeding is disabled when DATA_MODE != 'mock' (siehe docs/11).")
```

Guard im Produktions-Import (docs/11 B.1):

```python
def _require_prod():
    if os.environ.get("DATA_MODE") != "prod":
        sys.exit("REFUSED: import_production requires DATA_MODE=prod.")
```

Konfiguration (docs/02 §4), aus der die Werte stammen:

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    data_mode: str = "mock"
    min_cohort_k: int = 10
```

## Umsetzungsschritte

- [ ] Sicherstellen, dass `_guard_not_prod()` in `seed.py` sowohl beim Seeden als auch bei `--reset` zuerst aufgerufen wird (identischer Guard für beide Pfade).
- [ ] Sicherstellen, dass `_require_prod()` in `import_production.py` zu Beginn jeder Public-Funktion läuft.
- [ ] Guard-Logik zentralisieren (gemeinsamer Helfer, der `DATA_MODE` liest), um Drift zwischen den beiden Skripten zu vermeiden.
- [ ] `.env.example` dokumentiert `DATA_MODE=mock` und eine `localhost`-`DATABASE_URL`; Prod-`.env` (getrennt verwaltet) dokumentiert `DATA_MODE=prod` und eine CH/EU-`DATABASE_URL`.
- [ ] Doku-Hinweis ergänzen: **kein gemeinsamer Cluster** für Mock und Echtdaten.
- [ ] Optional (Defense-in-depth): bei `DATA_MODE=prod` prüfen, dass `DATABASE_URL` nicht auf `localhost`/`127.0.0.1` zeigt (siehe Hinweis).
- [ ] Verifizieren, dass `.env` in `.gitignore` steht (Prod-Secrets nie eingecheckt).

> Hinweis: zu entscheiden — ob der zusätzliche localhost-Check als harter Fehler oder nur als Warnung implementiert wird; der Plan fordert nur den `DATA_MODE`-Guard und getrennte URLs verbindlich.

## Akzeptanzkriterien

- [ ] Modus wird ausschliesslich über `DATA_MODE` gesteuert.
- [ ] Seeder/Reset sind bei `DATA_MODE != mock` gesperrt (Guard greift im Code, nicht nur in Doku).
- [ ] Produktions-Import verlangt `DATA_MODE == prod`.
- [ ] Prod und Dev nutzen verschiedene `DATABASE_URL`/Datenbanken; dokumentiert, dass kein gemeinsamer Cluster verwendet wird.

## Tests / Verifikation

- [ ] Seeder in Prod gesperrt: `$env:DATA_MODE='prod'; uv run python ../../scripts/seed.py --profile demo` → Exit mit `REFUSED: seeding is disabled ...`.
- [ ] Reset in Prod gesperrt: `$env:DATA_MODE='prod'; uv run python ../../scripts/seed.py --reset` → gleicher REFUSED-Exit.
- [ ] Import in Mock gesperrt: `$env:DATA_MODE='mock'; uv run python ../../scripts/import_production.py --roster x.csv` → Exit mit `REFUSED: import_production requires DATA_MODE=prod.`.
- [ ] `uv run pytest tests/test_guards.py -q` → grün (testet beide Richtungen; erwartet `SystemExit`).

## Abhängigkeiten

- **MOCK-1** — führt den `_guard_not_prod()`-Guard und den Seeder-Entrypoint ein, den dieser Task absichert/zentralisiert.
- **PROD-1** — liefert `import_production.py` mit dem `_require_prod()`-Guard, dessen Gegenrichtung hier getestet wird.
- Nachgelagert: alle Produktions-Deployments (PROD-3-Konfiguration) verlassen sich darauf, dass diese Guards greifen.

## Definition of Done

- [ ] Akzeptanzkriterien (oben, abgeleitet aus docs/11 B.2) erfüllt.
- [ ] Tests grün via `uv run pytest`; die Safety-Guard-Tests sind enthalten und belegen beide Richtungen.
- [ ] Keine PII in externen LLM-Prompts (für diesen Task nicht zutreffend — reiner Guard/Config-Pfad).
- [ ] `uv`-only, keine `pip`-Aufrufe.
- [ ] Zugehöriges GitHub-Issue PROD-2 geschlossen, E14-Epic-Checkliste aktualisiert.
