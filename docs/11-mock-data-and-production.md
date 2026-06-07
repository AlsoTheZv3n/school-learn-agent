# 11 — Mock-Data-Seeder & Produktionsdaten (E13, E14, M5)

**Ziel:** Ein Seeder, der realistische Demo-/Lastdaten erzeugt (Klassen, Schüler:innen, Skills,
plausible `attempts` + abgeleitete `learner_state`), **und** ein sauber getrennter Pfad für
echte Produktionsdaten — mit Guards, die verhindern, dass Mock-Daten je in Produktion landen.

**Voraussetzungen:** DB-2 (Modelle), LM-2 (Tracing), CON-2 (Ingestion für echtes Material).
**Issues:** MOCK-1 … MOCK-3 (Mock), PROD-1 … PROD-3 (Produktion).

---

## Teil A — Mock-Data-Seeder (E13)

### A.1 Seeder-CLI (MOCK-1)

`scripts/seed.py` als `uv`-Entrypoint, profilbasiert:

| Profil | Zweck | Umfang |
|---|---|---|
| `demo` | hübsche, kleine Vorführung | 1–2 Klassen, ~25 Schüler, 1 Fach |
| `load` | Last-/Aggregat-Tests | mehrere Klassen, ≥ `k` pro Kohorte, viele Attempts |
| `empty` | nur Stammdaten (Fächer/Skills), keine Personen | — |

Aufruf (Referenz):

```bash
cd apps/api
uv run python ../../scripts/seed.py --profile demo
uv run python ../../scripts/seed.py --profile load --classes 5 --students-per-class 24
uv run python ../../scripts/seed.py --reset      # nur Dev! (siehe MOCK-3)
```

Gerüst:

```python
# scripts/seed.py
import argparse, os, sys, uuid, random
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def _guard_not_prod():
    if os.environ.get("DATA_MODE", "mock") != "mock":
        sys.exit("REFUSED: seeding is disabled when DATA_MODE != 'mock' (siehe docs/11).")

def seed(profile: str, classes: int, students_per_class: int) -> None:
    _guard_not_prod()
    engine = create_engine(os.environ["DATABASE_URL"])
    Session = sessionmaker(bind=engine)
    with Session() as s:
        subjects, skills = _ensure_curriculum(s)          # Fächer + Skill-Graph (idempotent)
        if profile == "empty":
            s.commit(); return
        n_classes = 1 if profile == "demo" else classes
        n_students = 25 if profile == "demo" else students_per_class
        for _ in range(n_classes):
            klass = _make_class(s)
            students = [_make_student(s, klass) for _ in range(n_students)]
            for student in students:
                _simulate_history(s, student, skills)      # erzeugt attempts + learner_state
        s.commit()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", choices=["demo", "load", "empty"], default="demo")
    ap.add_argument("--classes", type=int, default=3)
    ap.add_argument("--students-per-class", type=int, default=20)
    ap.add_argument("--reset", action="store_true")
    args = ap.parse_args()
    if args.reset:
        _reset()       # MOCK-3
    else:
        seed(args.profile, args.classes, args.students_per_class)
```

**AK:** `--profile demo|load|empty`; legt Klassen/Schüler/Skills + `attempts` + abgeleitete
`learner_state` an; `uv`-Entrypoint.

### A.2 Realistische Lernkurven (MOCK-2)

Attempts dürfen **nicht** uniform-zufällig sein, sonst sind Mastery-Verteilungen unbrauchbar und
das Open Learner Model wirkt im Demo unecht. Stattdessen pro Schüler:in eine latente Fähigkeit
ziehen und Antworten daraus generieren — und die Mastery über **denselben** Tracing-Service
ableiten wie im Echtbetrieb (Konsistenz mit P3):

```python
from its.learner_model.tracing import record_attempt
from its.db.models import Attempt

def _simulate_history(s, student, skills, rng=random.Random()):
    ability = rng.betavariate(2, 2)              # latente Fähigkeit je Schüler:in (0..1)
    for skill in skills:
        n = rng.randint(4, 12)                   # Versuche je Skill
        for i in range(n):
            # Lernfortschritt: P(correct) steigt mit Übung, gedeckelt durch ability
            p_correct = min(0.95, ability * (0.5 + 0.05 * i))
            correct = rng.random() < p_correct
            s.add(Attempt(student_id=student.id, skill_id=skill.id,
                          item_ref=f"seed-{skill.key}-{i}", is_correct=correct))
            record_attempt(s, student.id, skill.id, correct)   # gleiche Logik wie live
```

**AK:** plausible, nicht-uniforme Mastery-Verläufe; `load`-Profil erzeugt Kohorten **≥ `k`**,
damit die Population-/Aggregat-Endpoints (RET-4) testbar sind.

### A.3 Reset/Teardown (MOCK-3)

`--reset` leert die personenbezogenen Tabellen (und optional Content) — **nur in Dev**:

```python
def _reset():
    _guard_not_prod()                            # identischer Guard wie beim Seeden
    engine = create_engine(os.environ["DATABASE_URL"])
    with engine.begin() as c:
        c.exec_driver_sql("TRUNCATE teacher_notes, attempts, learner_state, "
                          "enrollments, classes, students RESTART IDENTITY CASCADE;")
```

**AK:** `--reset` ist durch denselben Prod-Guard geschützt; ein versehentlicher Lauf gegen eine
Prod-DB ist nicht möglich.

---

## Teil B — Produktionsdaten & Compliance (E14)

### B.1 Produktiver Ingestion-Pfad (PROD-1)

`scripts/import_production.py` — getrennt vom Mock, **idempotent**, gegen validierte Schemata:

- Lernmaterial: über die **reguläre** Ingestion-Pipeline (CON-2) — echte Markdown-Notizen
  rein, Prosa embeddet, Query als Sidecar. Kein Sonderpfad fürs Embedding.
- Klassenlisten/Personen: aus einer validierten Quelle (z. B. CSV/Schul-API) über Pydantic-Modelle;
  Idempotenz über stabile externe Schlüssel (Upsert statt blindem Insert).
- **Niemals** Mock-Daten und Echtdaten in derselben DB mischen.

```python
# scripts/import_production.py (Skizze)
import os, sys
def _require_prod():
    if os.environ.get("DATA_MODE") != "prod":
        sys.exit("REFUSED: import_production requires DATA_MODE=prod.")
def import_roster(path: str) -> None:
    _require_prod()
    # validiere Zeilen (Pydantic), upsert students/classes/enrollments anhand externer IDs
    ...
def import_content(vault_dir: str) -> None:
    _require_prod()
    # nutze its.content.ingest (CON-2) — gleiche Pipeline wie Mock-Content
    ...
```

**AK:** echtes Material läuft über CON-2; Personen-Import idempotent; klar von Mock getrennt.

### B.2 Env-Toggle Mock/Prod + Guards (PROD-2) · `safety-critical`

Eine einzige Umgebungsvariable steuert den Modus, plus getrennte DB-URLs:

```dotenv
# .env (Dev)                         # .env (Prod, getrennt verwaltet)
DATA_MODE=mock                       DATA_MODE=prod
DATABASE_URL=...localhost...its      DATABASE_URL=...ch-region...its_prod
MIN_COHORT_K=10                      MIN_COHORT_K=10
```

Regeln (durchgesetzt im Code, nicht nur dokumentiert):
- `seed.py`/`--reset` **verweigern** sich bei `DATA_MODE != mock` (Guard aus A.1/A.3).
- `import_production.py` **verlangt** `DATA_MODE == prod`.
- Prod und Dev nutzen **verschiedene** `DATABASE_URL`/Datenbanken — kein gemeinsamer Cluster
  für Mock und Echtdaten.

**AK:** Modus per `DATA_MODE`; Seeder in Prod gesperrt; getrennte DB-URLs; Guards greifen im Code.

### B.3 Datenresidenz & Retention (PROD-3) · `priority:critical`

Da es um **Minderjährige** geht, ist dieser Punkt Voraussetzung, kein Anhang (P8). Festzuhalten
und zu konfigurieren:

- **Residenz:** Datenbank und LLM-Inferenz (falls extern) in **CH/EU-Region** (z. B. Azure
  Switzerland, Exoscale, Infomaniak). Prototyp-Hosting (Railway o. Ä.) ist **nicht** für Echtdaten.
- **PII-Minimierung:** Schema hält bereits wenig PII (docs/03); LLM-Pfad ist anonymisiert (P4).
- **Retention/Löschung:** definiertes Aufbewahrungsfenster pro Datenkategorie; Löschpfad für
  einzelne Schüler:innen (CASCADE über `ON DELETE CASCADE` ist im Schema vorbereitet).
- **Auftragsverarbeitung:** falls eine externe LLM-API genutzt wird, ist ein
  Auftragsverarbeitungsvertrag (AVV/DPA) und ein No-Training-Setting erforderlich; sonst lokales
  Modell.

> **Rechtliche Detailangaben gegen aktuelle Quellen prüfen.** revDSG (CH) und DSGVO (EU) sowie
> kantonale/schulische Vorgaben für Ed-Tech ändern sich; die hier genannten Punkte sind die
> Architektur-Leitplanken, **kein** Rechtsrat. Vor Produktivbetrieb mit echten Schülerdaten ist
> eine fachliche/rechtliche Prüfung einzuholen.

**AK:** dokumentierte + konfigurierte Residenz (CH/EU), Retention-/Löschkonzept, AVV-Anforderung
bei externer LLM-Nutzung; rechtliche Angaben als gegen aktuelle Quellen zu prüfen markiert.

---

## Konsistenz mit übrigem Plan

- `DATA_MODE` und `MIN_COHORT_K` stammen aus `.env.example` (docs/02 §3).
- Der Seeder leitet Mastery über `record_attempt` (docs/06) ab — **dieselbe** Logik wie live (P3).
- `load`-Profil erfüllt die Kohorten-Voraussetzung für die Population-Tests (docs/05, RET-4).

---

## Akzeptanzkriterien (gesamt)

- [ ] `scripts/seed.py` mit `--profile demo|load|empty`; `uv`-Entrypoint (MOCK-1)
- [ ] realistische, nicht-uniforme Lernkurven; `load` erzeugt Kohorten ≥ `k` (MOCK-2)
- [ ] `--reset` durch Prod-Guard geschützt (MOCK-3)
- [ ] `import_production.py` idempotent, über CON-2, getrennt von Mock (PROD-1)
- [ ] `DATA_MODE`-Toggle; Seeder in Prod gesperrt; getrennte DB-URLs (PROD-2)
- [ ] Residenz CH/EU + Retention/Löschung + AVV dokumentiert/konfiguriert; rechtlich zu prüfen markiert (PROD-3)

---

## Claude-Code-Prompt

```
Setze E13 + E14 (docs/11-mock-data-and-production.md) um: scripts/seed.py (uv-Entrypoint,
--profile demo|load|empty, --reset; Prod-Guard via DATA_MODE; erzeugt Klassen/Schüler/Skills,
attempts und leitet learner_state über record_attempt ab — gleiche Logik wie live; nicht-uniforme
Lernkurven; load-Profil mit Kohorten >= MIN_COHORT_K). Dann scripts/import_production.py
(idempotenter Personen-Import über Pydantic-Validierung + Content über its.content.ingest;
verlangt DATA_MODE=prod). Setze die Guards im Code durch (Seeder/Reset nur bei DATA_MODE=mock).
Dokumentiere Residenz CH/EU + Retention/Löschung + AVV in einer Doku-Datei und markiere die
rechtlichen Angaben als gegen aktuelle Quellen zu prüfen. Schliesse MOCK-1..3 und PROD-1..3.
```
