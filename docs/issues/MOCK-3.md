## Ziel

Ein `--reset`-Pfad, der die personenbezogenen Tabellen leert (`teacher_notes`, `attempts`, `learner_state`, `enrollments`, `classes`, `students`) — ausschließlich in der Entwicklung. Er ist durch **denselben** Prod-Guard geschützt wie das Seeden, sodass ein versehentlicher Lauf gegen eine Prod-DB strukturell unmöglich ist.

## Kontext & Prinzipien

- **P1 (Safety zuerst, in der DB verankert):** Ein Reset ist die gefährlichste Operation des Seeders. Der identische `_guard_not_prod()` wie beim Seeden (A.1/A.3) verhindert Datenverlust in Produktion — durchgesetzt im Code, nicht nur dokumentiert.
- **P8 (Datenresidenz / Dev-Prod-Trennung):** Reset darf nie die CH/EU-Prod-DB treffen; in Kombination mit getrennten DB-URLs (PROD-2, E14) ist der Pfad doppelt abgesichert.
- **Symmetrie zum Seed-Guard:** Es darf KEINE asymmetrische Lücke geben, durch die ein Reset ohne Guard durchschlüpft — dieselbe Funktion bewacht beide Pfade.
- **P9 (`uv` ausschließlich):** Aufruf über `uv run`.

## Zu erstellende/ändernde Dateien

- `scripts/seed.py` — `_reset()` implementieren und im `__main__`-Block verdrahten (Datei aus MOCK-1).

## Schnittstellen & Signaturen

Referenz aus docs/11 (A.3) — autark zu reproduzieren:

```python
def _reset():
    _guard_not_prod()                            # identischer Guard wie beim Seeden
    engine = create_engine(os.environ["DATABASE_URL"])
    with engine.begin() as c:
        c.exec_driver_sql("TRUNCATE teacher_notes, attempts, learner_state, "
                          "enrollments, classes, students RESTART IDENTITY CASCADE;")
```

Guard (identisch zu MOCK-1, A.1):

```python
def _guard_not_prod():
    if os.environ.get("DATA_MODE", "mock") != "mock":
        sys.exit("REFUSED: seeding is disabled when DATA_MODE != 'mock' (siehe docs/11).")
```

Verdrahtung im `__main__`-Block (aus dem CLI-Gerüst, MOCK-1):

```python
if args.reset:
    _reset()       # MOCK-3
else:
    seed(args.profile, args.classes, args.students_per_class)
```

## Umsetzungsschritte

- [ ] `_reset()` gemäß Referenz implementieren: zuerst `_guard_not_prod()` aufrufen (vor jeglichem DB-Zugriff).
- [ ] Engine über `os.environ["DATABASE_URL"]` aufbauen; Transaktion über `engine.begin()`.
- [ ] `TRUNCATE teacher_notes, attempts, learner_state, enrollments, classes, students RESTART IDENTITY CASCADE;` via `exec_driver_sql` ausführen — vollständige Tabellenliste in EINER Anweisung (deckt FK-Abhängigkeiten via `CASCADE`).
- [ ] Stammdaten (`subjects`, `skills`, `skill_edges`, `content_*`) NICHT truncaten — Curriculum bleibt erhalten (idempotent neu seedbar). Content-Reset nur als separate, ausgeschaltete Option erwägen.
- [ ] Im `__main__`-Block sicherstellen: `--reset` ruft `_reset()` auf und führt NICHT zusätzlich `seed(...)` aus.
- [ ] Klare Konsolenausgabe nach erfolgreichem Reset (welche Tabellen geleert wurden).

## Akzeptanzkriterien

- [ ] `--reset` leert genau die personenbezogenen Tabellen (`teacher_notes`, `attempts`, `learner_state`, `enrollments`, `classes`, `students`).
- [ ] `--reset` ist durch denselben `_guard_not_prod()` geschützt wie das Seeden; bei `DATA_MODE != mock` bricht es mit `REFUSED:` und Exit-Code != 0 ab, BEVOR ein `TRUNCATE` ausgeführt wird.
- [ ] Stammdaten/Curriculum bleiben nach `--reset` erhalten.
- [ ] `--reset` führt nicht zusätzlich einen Seed-Lauf aus.

## Tests / Verifikation

```bash
cd apps/api
# Vorbereitung: Demo-Daten anlegen
DATA_MODE=mock uv run python ../../scripts/seed.py --profile demo
# Reset in Dev:
DATA_MODE=mock uv run python ../../scripts/seed.py --reset
# Guard greift auch beim Reset:
DATA_MODE=prod uv run python ../../scripts/seed.py --reset    # erwartet: REFUSED..., Exit != 0
```

Erwartete Ergebnisse:
- Nach `--reset` (Dev): `SELECT count(*) FROM students;` und `... FROM attempts;` und `... FROM learner_state;` liefern jeweils 0; `SELECT count(*) FROM skills;` bleibt unverändert (> 0).
- Mit `DATA_MODE=prod`: Ausgabe beginnt mit `REFUSED:`, keine Tabelle wird geleert.

> Hinweis: zu entscheiden — ob ein optionaler Content-Reset (`--reset-content` über `content_notes`/`content_embeddings`/`skills`/`subjects`/`skill_edges`) ergänzt wird; wegen FK-Abhängigkeiten von `attempts.skill_id`/`learner_state.skill_id` standardmäßig AUS (siehe Epic-Planung offene Fragen 4 und 6).

## Abhängigkeiten

- **MOCK-1** (Seeder-CLI): liefert `_guard_not_prod()`, den `--reset`-Schalter und das CLI-Gerüst, in das `_reset()` verdrahtet wird.
- Nachgelagert: **PROD-2** (E14, getrennte DB-URLs + `DATA_MODE`-Härtung) ergänzt die zweite Schutzschicht; der Reset-Guard ist die erste.

## Definition of Done

- [ ] Akzeptanzkriterien (oben, abgeleitet aus docs/11 A.3) erfüllt.
- [ ] Tests grün, inkl. Nachweis, dass der Guard den Reset bei `DATA_MODE=prod` verweigert.
- [ ] Kein LLM betroffen; keine PII in externen Prompts (n/a).
- [ ] `uv`-only; keine `pip`-Aufrufe.
- [ ] GitHub-Issue MOCK-3 geschlossen, Epic-E13-Checkliste aktualisiert.

