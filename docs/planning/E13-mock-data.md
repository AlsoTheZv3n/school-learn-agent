# E13 — Mock-Data-Seeder — Detailplanung

## 1. Scope & Zielbild

Das Epic E13 liefert einen profilbasierten **Mock-Data-Seeder** (`scripts/seed.py`), der realistische Demo- und Lastdaten in eine **Dev-Datenbank** schreibt: Stammdaten (Fächer, Skills, `skill_edges`), Personen (Klassen, Schüler:innen, Enrollments) sowie plausible `attempts` mit daraus **über denselben Tracing-Service wie im Echtbetrieb** abgeleitetem `learner_state`. Dazu gehört ein durch einen Prod-Guard geschützter Reset-Pfad.

Abgrenzung (NICHT in E13, sondern E14): der produktive Ingestion-Pfad (`scripts/import_production.py`), das `DATA_MODE`-Toggle als Gesamt-Compliance-Konzept inkl. getrennter DB-URLs (PROD-2) und die Residenz-/Retention-Dokumentation (PROD-3). E13 nutzt den Guard und das `DATA_MODE`-Konzept aber bereits aktiv: der Seeder verweigert sich bei `DATA_MODE != mock`.

Zielzustand am Ende von E13:
- `uv run python ../../scripts/seed.py --profile demo|load|empty` läuft als `uv`-Entrypoint und befüllt die DB.
- Mastery-Verteilungen sind nicht-uniform und plausibel (latente Fähigkeit je Schüler:in + Lernkurve), abgeleitet via `record_attempt` (LM-2) — Konsistenz mit P3.
- Das `load`-Profil erzeugt Kohorten mit `n >= MIN_COHORT_K`, sodass die Population-Endpoints (RET-4) testbar werden.
- `--reset` ist durch denselben Prod-Guard geschützt wie das Seeden; ein versehentlicher Lauf gegen eine Prod-DB ist unmöglich.

## 2. Task-Reihenfolge & Abhängigkeiten

```
DB-2 (SQLAlchemy-Modelle) ─┐
                           ├─> MOCK-1 (Seeder-CLI + Guard + Curriculum/Personen)
LM-2 (record_attempt) ─────┘        │
                                    ├─> MOCK-2 (realistische Lernkurven, _simulate_history)
                                    └─> MOCK-3 (Reset/Teardown mit Prod-Guard)
```

- **MOCK-1** ist die Wurzel des Epics: CLI-Gerüst, Prod-Guard, Curriculum-Seed (idempotent), Klassen/Schüler/Enrollments, Aufruf von `_simulate_history` als noch zu konkretisierende Funktion.
- **MOCK-2** und **MOCK-3** hängen beide nur an MOCK-1 und sind untereinander unabhängig — können parallel umgesetzt werden.
- MOCK-2 füllt `_simulate_history` mit Inhalt (Lernkurven) und garantiert die `load`-Kohortengröße.
- MOCK-3 ergänzt `_reset()` und verdrahtet den `--reset`-Schalter.

Nachgelagert (außerhalb E13): PROD-2 (E14) härtet das `DATA_MODE`-Toggle und getrennte DB-URLs; die Population-Tests (RET-4, E4) konsumieren die vom `load`-Profil erzeugten Kohorten.

## 3. Feinere Sub-Task-Zerlegung (über die Issues hinaus)

**MOCK-1**
- `scripts/seed.py` als ausführbares Skript mit `argparse`-Frontend (Profile, `--classes`, `--students-per-class`, `--reset`).
- `_guard_not_prod()` — liest `DATA_MODE` aus der Umgebung, `sys.exit` bei `!= mock`.
- Engine/Session-Aufbau über `os.environ["DATABASE_URL"]` (Seeder ist ein DB-Admin-Skript, läuft NICHT durch `scoped_session`/RLS — siehe Designentscheidung D2).
- `_ensure_curriculum(s)` — idempotenter Upsert von Fach `math`, Skills (`linear-equations`, `complete-the-square`, `quadratic-formula`) und `skill_edges` (prerequisite-Kette). Idempotenz über `subjects.key` / `(subject_id, skills.key)` UNIQUE.
- `_make_class(s)` / `_make_student(s, klass)` / Enrollment-Erzeugung.
- Profil-Logik: `empty` → nur Curriculum; `demo` → 1 Klasse, 25 Schüler; `load` → `--classes` × `--students-per-class`.
- `_simulate_history`-Aufruf je Schüler:in (Implementierung in MOCK-2).
- Ein abschließender `s.commit()`.

**MOCK-2**
- `_simulate_history(s, student, skills, rng)` — latente Fähigkeit per `betavariate(2,2)`, je Skill 4–12 Versuche, ansteigende `p_correct` gedeckelt durch `ability`.
- Pro Versuch: `Attempt(...)`-Insert UND `record_attempt(s, student.id, skill.id, correct)` (LM-2) — dieselbe Logik wie live.
- Seedbares `rng` (deterministischer Seed-Parameter) für reproduzierbare Demos — Vorschlag: `--seed`-CLI-Argument an `seed()` durchreichen.
- `load`-Garantie: `n_students >= MIN_COHORT_K` validieren bzw. dokumentieren, damit jede Klassen-Kohorte die RET-4-Schwelle überschreitet.

**MOCK-3**
- `_reset()` mit identischem `_guard_not_prod()`.
- `TRUNCATE teacher_notes, attempts, learner_state, enrollments, classes, students RESTART IDENTITY CASCADE;` via `engine.begin()` / `exec_driver_sql`.
- Verdrahtung `if args.reset: _reset()` im `__main__`-Block.
- Optionaler Content-Reset (Notiz: zu entscheiden, siehe offene Fragen).

## 4. Zentrale Designentscheidungen mit Begründung

- **D1 — Mastery niemals direkt schreiben, immer über `record_attempt` (P3).** Der Seeder simuliert nur Beobachtungen (`is_correct`) und lässt `learner_state` durch denselben BKT-Tracing-Service berechnen wie der Live-Pfad. So bleiben Demo-Verteilungen mit dem echten Modellverhalten konsistent und das Open Learner Model (P5) wirkt echt.
- **D2 — Seeder umgeht RLS bewusst, läuft aber NICHT in Prod (P1).** Der Seeder ist ein Admin-/Bootstrapping-Skript und schreibt klassenübergreifend; er verbindet sich als DB-Owner (`its`), nicht über `scoped_session`. Die Isolations-Garantie für Endnutzer (RLS) bleibt unberührt, weil der Seeder ausschließlich gegen Dev-DBs läuft — durchgesetzt durch den Prod-Guard.
- **D3 — Ein einziger Guard (`_guard_not_prod`) für Seed UND Reset.** Genau dieselbe Funktion bewacht beide Pfade (A.1/A.3), damit es keine asymmetrische Lücke gibt, durch die ein Reset gegen Prod durchschlüpft.
- **D4 — Idempotentes Curriculum, frische Personen.** Stammdaten (Fächer/Skills/Edges) werden upsertet (mehrfaches `--profile empty`/`demo` darf nicht duplizieren); Personen werden additiv erzeugt (für `load` gewollt) und nur über `--reset` entfernt.
- **D5 — Nicht-uniforme Lernkurven statt `random.random()` für `is_correct`.** Eine latente Fähigkeit je Schüler:in plus Übungsfortschritt erzeugt eine realistische Mastery-Verteilung; uniform-zufällige Antworten würden BKT in unbrauchbares Rauschen treiben.
- **D6 — Reproduzierbarkeit über seedbares RNG.** Für verlässliche Demos und Tests sollte der Zufall deterministisch seedbar sein (siehe offene Frage zur CLI-Flagge).

## 5. Risiken & Gegenmaßnahmen

- **Mock-Daten landen in Prod** → Doppelter Guard (Seed + Reset), `sys.exit` mit klarer Meldung; in E14/PROD-2 zusätzlich getrennte DB-URLs.
- **`record_attempt` committet/flusht selbst nicht** → Seeder steuert Transaktion zentral (`s.commit()` am Ende); bei großen `load`-Läufen Batch-Commits, um Speicher/Locks zu begrenzen.
- **`load`-Kohorte < `k`** → Default `--students-per-class` muss `>= MIN_COHORT_K` (10) sein bzw. der Seeder validiert/warnt, sonst sind RET-4-Tests nicht erfüllbar.
- **Performance bei `load`** → `record_attempt` pro Versuch ist N+1-lastig; Maßnahme: Bulk-Inserts für `attempts`, Tracing weiterhin über den Service, ggf. periodische Flushes.
- **TRUNCATE-Reihenfolge / FK-Verletzungen** → `CASCADE` + vollständige Tabellenliste in einer Anweisung deckt FK-Abhängigkeiten ab; `RESTART IDENTITY` setzt Sequenzen zurück.

## 6. Offene Fragen / zu treffende Entscheidungen

1. **Seedbares RNG / `--seed`-Flagge:** Im Doc ist `rng=random.Random()` ein nicht geseedeter Default. Für reproduzierbare Demos/Tests sollte ein expliziter Seed wählbar sein. → Empfehlung: `--seed`-Argument hinzufügen, an `seed()`/`_simulate_history` durchreichen, Default fix (z. B. 42).
2. **`--students-per-class`-Default vs. `MIN_COHORT_K`:** Default ist 20, `MIN_COHORT_K` ist 10 — passt; aber `--students-per-class` kann unter 10 gesetzt werden und bricht dann RET-4. → Empfehlung: Im `load`-Profil eine Validierung/Warnung, dass jede Klasse `>= MIN_COHORT_K` Schüler haben sollte.
3. **`item_ref`-Schema:** Doc nutzt `f"seed-{skill.key}-{i}"`. Ob diese Refs auf reale Items aus dem Grading-/Content-Pfad zeigen müssen, ist offen — vermutlich nicht (Mock). → Empfehlung: synthetische `seed-…`-Refs belassen, da Grading im Seeder nicht aufgerufen wird.
4. **Content-Reset in `_reset()`:** A.3 sagt „und optional Content". Welche Tabellen (z. B. `content_notes`, `content_embeddings`, `skills`, `subjects`, `skill_edges`)? → Empfehlung: Personen-Tabellen wie im Doc truncaten; Content-Reset als separate, ausgeschaltete Option (`--reset-content`) lassen, da Curriculum idempotent ist.
5. **Engine-Verbindung als welcher DB-User:** Der Seeder nutzt `DATABASE_URL` direkt. Damit RLS umgangen wird, muss das der Owner (`its`) sein, nicht `its_student`. → Empfehlung: dokumentieren, dass `DATABASE_URL` auf den privilegierten Dev-User zeigt; kein `SET ROLE`.
6. **`subjects`/`skills`-IDs in `attempts`/`learner_state`:** `attempts.skill_id` referenziert `skills.id` ohne `ON DELETE CASCADE` im Schema. Beim Content-Reset könnten FKs brechen — bestärkt Empfehlung aus (4), Content nicht standardmäßig zu truncaten.

## 7. Test-/Verifikationsstrategie für das Epic

- **Smoke (MOCK-1):** `DATA_MODE=mock` → `--profile empty` legt genau Curriculum an (Re-Run dupliziert nicht); `--profile demo` legt 1 Klasse / 25 Schüler / `attempts` / `learner_state` an.
- **Guard (MOCK-1/MOCK-3):** Mit `DATA_MODE=prod` müssen sowohl `seed` als auch `--reset` mit `REFUSED:`-Meldung und Exit-Code != 0 abbrechen; gegen die DB darf keine Zeile geschrieben/gelöscht werden.
- **Lernkurven (MOCK-2):** Über die `learner_state`-Verteilung prüfen, dass Mastery-Werte gestreut und nicht uniform sind (z. B. Histogramm/Varianz); jeder Wert in `[0,1]`.
- **Kohorte (MOCK-2 → RET-4):** Nach `--profile load` muss `skill_mastery_distribution` für jede Klasse `n >= MIN_COHORT_K` liefern und NICHT `CohortTooSmall` werfen.
- **Reset (MOCK-3):** Nach `--profile demo` dann `--reset` → personenbezogene Tabellen leer, Curriculum bleibt erhalten.
- Alle Befehle als `uv run` (P9); keine `pip`-Aufrufe.

