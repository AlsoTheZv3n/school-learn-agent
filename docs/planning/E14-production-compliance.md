# E14 — Produktionsdaten & Compliance — Detailplanung

> Quelle: `docs/11-mock-data-and-production.md` (Teil B), verankert in `docs/00-architecture.md` (Prinzipien P1-P9, Repo-Layout §6, DoD §8). Ergänzend: `docs/02-foundations.md` (Env/Config), `docs/03-database.md` (Schema/CASCADE/Modelle), `docs/04-safety.md` (RLS), `docs/05-retrieval.md` (CON-2 Ingestion), `docs/07-agent.md` (LLM-Client/Anonymisierung).

## 1. Scope & Zielbild

E14 schliesst die Lücke zwischen "schöner Demo mit Mock-Daten" (E13) und "echtem Betrieb mit Daten Minderjähriger". Das Epic liefert drei Bausteine:

1. **PROD-1 — Produktiver Ingestion-Pfad:** ein eigenständiges, idempotentes Import-Skript (`scripts/import_production.py`), das echtes Lernmaterial über die *reguläre* CON-2-Pipeline einspeist und Klassenlisten/Personen aus einer validierten Quelle (Pydantic) per Upsert über stabile externe Schlüssel anlegt — strikt getrennt vom Mock-Seeder.
2. **PROD-2 — Env-Toggle Mock/Prod + Guards (`safety-critical`):** eine einzige Umgebungsvariable `DATA_MODE` plus getrennte `DATABASE_URL`s steuert den Modus; Guards werden *im Code* durchgesetzt (Seeder/Reset nur bei `DATA_MODE=mock`, Import nur bei `DATA_MODE=prod`), damit Mock- und Echtdaten nie in derselben DB landen.
3. **PROD-3 — Datenresidenz & Retention (`priority:critical`):** dokumentierte und konfigurierte CH/EU-Residenz für DB und (externe) LLM-Inferenz, ein Retention-/Löschkonzept pro Datenkategorie (gestützt auf `ON DELETE CASCADE` aus dem Schema), und die AVV/No-Training-Anforderung bei externer LLM-Nutzung — rechtliche Angaben explizit als "gegen aktuelle Quellen zu prüfen" markiert.

Zielbild am Ende des Epics: Ein neues Schul-Deployment kann (a) echte Inhalte und Rosters reproduzierbar importieren, (b) niemals versehentlich Mock-Daten in Prod erzeugen, und (c) eine prüfbare Compliance-Grundlage (Residenz/Retention/Löschung/AVV) vorweisen.

## 2. Task-Reihenfolge & Abhängigkeiten

```
CON-2 ─┐
       ├─> PROD-1 ─┐
DB-2 ──┘           ├─> PROD-2  (braucht zusätzlich MOCK-1 für den geteilten Guard)
MOCK-1 ────────────┘

PROD-3  (unabhängig — kann parallel ab Tag 1 laufen)
```

- **PROD-3** hat keine Code-Abhängigkeit und sollte zuerst/parallel starten, weil es Architektur-Leitplanken setzt (Residenz/Retention), die PROD-1/PROD-2 voraussetzen (z. B. "Prod-DB liegt in CH/EU", "kein gemeinsamer Cluster").
- **PROD-1** braucht CON-2 (Ingestion-Pipeline `its.content.ingest`) und DB-2 (SQLAlchemy-Modelle für Upsert).
- **PROD-2** braucht MOCK-1 (der `_guard_not_prod`-Guard wird dort eingeführt und hier geteilt/zentralisiert) und PROD-1 (der `_require_prod`-Guard für den Import).

Empfohlene Bearbeitungsreihenfolge: PROD-3 (Doku/Config) parallel, dann PROD-1, dann PROD-2 (schliesst die Guards code-seitig final).

## 3. Feinere Sub-Task-Zerlegung (über die Issues hinaus)

**PROD-1**
- 1a. Pydantic-Modelle für eine Roster-Zeile (`RosterRow`: externe Schüler-ID, Anzeigename, Stufe, Klassen-Schlüssel) definieren.
- 1b. CSV/Quelle einlesen + zeilenweise validieren; ungültige Zeilen sammeln und am Ende mit Zeilennummer melden (kein Teil-Commit eines kaputten Imports).
- 1c. Upsert-Logik: `external_id` als stabilen Schlüssel verwenden; `INSERT ... ON CONFLICT DO UPDATE` (oder SQLAlchemy-Äquivalent) für `students`/`classes`/`enrollments`.
- 1d. Content-Import: über `its.content.ingest` (kein Sonderpfad fürs Embedding), Vault-Verzeichnis rekursiv durchlaufen, Idempotenz über `content_notes.source_path`.
- 1e. `_require_prod()`-Guard am Anfang jeder Public-Funktion.
- 1f. CLI-Argumente (`--roster <path>`, `--vault <dir>`) und `uv`-Entrypoint.
- 1g. Dry-Run-Flag (`--dry-run`) zur Validierung ohne Schreiben (empfohlen, siehe offene Fragen).

> Hinweis: zu entscheiden — das Schema (`docs/03`) hat aktuell **keine** Spalte `external_id` auf `students`/`classes`. Für stabile Upserts ist eine zusätzliche Migration nötig (siehe offene Fragen).

**PROD-2**
- 2a. Guard-Helfer zentralisieren (statt Duplikat in `seed.py` und `import_production.py`): eine gemeinsame Funktion, die `DATA_MODE` liest.
- 2b. `seed.py`/`--reset`: `_guard_not_prod()` (verweigert bei `DATA_MODE != mock`).
- 2c. `import_production.py`: `_require_prod()` (verlangt `DATA_MODE == prod`).
- 2d. Getrennte `DATABASE_URL`s dokumentieren (`.env.example` vs. Prod-`.env`), inkl. expliziter Warnung "kein gemeinsamer Cluster".
- 2e. Optionaler Zusatz-Guard: bei `DATA_MODE=prod` prüfen, dass `DATABASE_URL` nicht auf `localhost` zeigt (Defense-in-depth, siehe offene Fragen).
- 2f. Tests für beide Guard-Richtungen (Seeder refused in prod, Import refused in mock).

**PROD-3**
- 3a. Doku-Datei `docs/compliance.md` (oder `infra/COMPLIANCE.md`) mit Residenz/Retention/Löschung/AVV.
- 3b. Retention-Tabelle pro Datenkategorie (attempts, learner_state, teacher_notes, students/PII, content).
- 3c. Löschpfad pro Schüler:in dokumentieren + via CASCADE belegen (Delete `students` → kaskadiert auf `enrollments`, `attempts`, `learner_state`, `teacher_notes`).
- 3d. Konfigurationshinweise: Region in der Deploy-Config (`infra/`) festhalten; `LLM_BACKEND=local` als Default für Echtdaten, `frontier` nur mit AVV + No-Training.
- 3e. Rechtlicher Disclaimer ("kein Rechtsrat, vor Produktivbetrieb fachliche Prüfung").
- 3f. Optionales Lösch-Skript/Funktion (`delete_student(external_id|id)`), siehe offene Fragen.

## 4. Zentrale Designentscheidungen (mit Begründung)

- **Zwei getrennte Skripte statt eines Modus-Flags im Seeder:** `scripts/seed.py` (Mock) und `scripts/import_production.py` (Prod) sind physisch getrennt. Begründung: Ein einziges Skript mit Modus-Switch erhöht das Risiko, dass Mock-Code-Pfade versehentlich gegen Prod laufen. Trennung + gegensätzliche Guards = Defense-in-depth.
- **Guard im Code, nicht nur in Doku:** `DATA_MODE` wird zur Laufzeit geprüft und führt zu `sys.exit(...)`. Begründung: P1-Geist ("Safety als Eigenschaft, nicht als Disziplin") auf Operationsebene übertragen.
- **Idempotenz über stabile externe Schlüssel (Upsert):** Re-Import desselben Rosters darf keine Duplikate erzeugen. Begründung: Schulen liefern Listen periodisch neu; blinder Insert würde Schüler verdoppeln und Kohortenzahlen (Min-Cohort) verfälschen.
- **Kein Sonderpfad fürs Embedding:** Content läuft durch dieselbe CON-2-Pipeline wie Mock-Content. Begründung: Eine zweite Embedding-Implementierung würde Retrieval-Qualität divergieren lassen; "nur Prosa embedden, Query als Sidecar" (P2-nahe Kernregel) muss in beiden Pfaden identisch gelten.
- **Lokales LLM als Default für Echtdaten:** `LLM_BACKEND=local` ist für Prod der sichere Default (P4/P8); `frontier` nur mit AVV + No-Training + CH/EU-Inferenz.
- **Löschung über CASCADE statt manuellem Delete-Sweep:** Das Schema hat bereits `ON DELETE CASCADE` auf den schülerbezogenen FKs; der Löschpfad nutzt das, statt jede Tabelle einzeln zu leeren. Begründung: weniger Vergessens-Risiko, Schema ist die Quelle der Wahrheit.

## 5. Risiken & Gegenmassnahmen

- **Versehentlicher Seed/Reset gegen Prod-DB** → Guard `DATA_MODE != mock` + getrennte `DATABASE_URL` + (optional) localhost-Check. Tests beweisen beide Guard-Richtungen.
- **Mock- und Echtdaten im selben Cluster** → Doku + Convention "verschiedene DBs"; optionaler DSN-Check; CI/Deploy stellt sicher, dass Prod-`.env` nicht eingecheckt wird (`.env` ist in `.gitignore`, docs/02 §1).
- **Duplikate beim Re-Import** → Upsert über externe Schlüssel; Test mit doppeltem Import → gleiche Zeilenzahl.
- **PII an externes LLM** → Echtdaten-Default `LLM_BACKEND=local`; falls `frontier`, greift `scrub()` (docs/07) + AVV/No-Training. Compliance-Doku hält das fest.
- **Fehlende `external_id`-Spalte** → blockiert idempotenten Upsert; als offene Frage + Migration eingeplant.
- **Rechtliche Fehlannahmen** → Disclaimer + Markierung "gegen aktuelle Quellen prüfen"; vor Go-Live fachliche/rechtliche Prüfung.
- **Teil-Commit bei kaputtem Roster** → Validierung vor Schreiben, Transaktion, Sammeln aller Fehler statt Abbruch nach erstem Insert.

## 6. Offene Fragen / zu treffende Entscheidungen

- Stabiler externer Schlüssel: Schema hat keine `external_id`-Spalte → braucht Migration; Default-Empfehlung: `students.external_id text UNIQUE`, `classes.external_key text UNIQUE`.
- Roster-Quellformat (CSV vs. Schul-API) und exaktes Spaltenschema sind im Plan nicht festgelegt.
- Lösch-Werkzeug: nur dokumentierter SQL-Pfad oder ein ausführbares `delete_student`-CLI?
- Konkrete Retention-Fristen pro Kategorie (Zahlenwerte) sind nicht spezifiziert — Architektur-Leitplanke ist da, Werte fehlen.
- CH/EU-Provider-Wahl (Azure Switzerland / Exoscale / Infomaniak) ist offen.
- Embedding-Modell/Dimension: Schema nutzt `vector(1024)` als Platzhalter; betrifft PROD-1 indirekt (Content-Import nutzt dieselbe Pipeline).

## 7. Test-/Verifikationsstrategie für das Epic

- **Guard-Tests (PROD-2, höchste Priorität):** Unit-Tests, die mit gesetztem `DATA_MODE` beide Skripte aufrufen und auf `SystemExit` prüfen (Seeder in prod, Import in mock).
- **Idempotenz-Test (PROD-1):** Roster zweimal importieren (gegen Test-DB mit `DATA_MODE=prod`) → identische Zeilenzahl, keine Duplikate.
- **Content-Pfad-Test (PROD-1):** Import eines Mini-Vaults → `content_notes`/`content_embeddings` angelegt, nur Prosa embeddet (keine SQL-Tokens im Chunk), `sidecar_query` gesetzt.
- **Doku-Review (PROD-3):** Checkliste, dass Residenz/Retention/Löschung/AVV + Disclaimer vorhanden sind; CASCADE-Löschpfad mit einem SQL-Smoke-Test belegt (`DELETE FROM students WHERE id=...` → abhängige Zeilen weg).
- Alle Python-Tests laufen via `uv run pytest` (P9), keine `pip`-Aufrufe.
