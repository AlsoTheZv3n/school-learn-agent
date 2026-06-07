## Ziel

Ein profilbasierter Seeder `scripts/seed.py` als `uv`-Entrypoint, der mit `--profile demo|load|empty` Stammdaten (Fächer, Skills, `skill_edges`) idempotent anlegt und je nach Profil Klassen, Schüler:innen und Enrollments erzeugt. Pro Schüler:in wird die Lernhistorie (`attempts` + abgeleiteter `learner_state`) über `_simulate_history` erzeugt (Implementierung in MOCK-2). Ein Prod-Guard verhindert jeden Lauf außerhalb von `DATA_MODE=mock`.

## Kontext & Prinzipien

- **P1 (Safety zuerst, in der DB verankert):** Der Seeder ist ein Admin-Skript, das klassenübergreifend schreibt und damit RLS NICHT durchläuft. Genau deshalb darf er ausschließlich gegen Dev-DBs laufen — durchgesetzt durch `_guard_not_prod()`, der bei `DATA_MODE != mock` sofort abbricht. Die produktive Isolation der Endnutzer bleibt unberührt.
- **P3 (Das Learner-Modell verbessert sich, nicht der Agent):** Der Seeder schreibt `learner_state` NIE direkt, sondern simuliert nur Beobachtungen und lässt die Mastery durch denselben Tracing-Service ableiten wie der Live-Pfad. MOCK-1 stellt dafür den Aufruf-Rahmen (`_simulate_history`) bereit.
- **P8 (Datenresidenz CH/EU) / Dev-Prod-Trennung:** `DATABASE_URL` und `DATA_MODE` kommen aus der Umgebung; der Guard ist die Code-seitige Garantie, dass Mock-Daten nicht in die CH/EU-Prod-DB gelangen.
- **P9 (`uv` ausschließlich):** Aufruf über `uv run python ../../scripts/seed.py`, kein `pip`, keine globale Python-Ausführung.

## Zu erstellende/ändernde Dateien

- `scripts/seed.py` — neu (Repo-Root `scripts/`, gemäß docs/02 §1 Monorepo-Struktur).
- Nutzt bestehende Module aus `apps/api/src/its/db/models.py` (DB-2) und `apps/api/src/its/learner_model/tracing.py` (LM-2, via MOCK-2). Keine Änderung an diesen Dateien.

## Schnittstellen & Signaturen

Gerüst aus docs/11 (A.1) — autark zu reproduzieren:

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

Relevante Modelle aus `db/models.py` (DB-2, docs/03 §4) zur Orientierung:

```python
class Student(Base):
    __tablename__ = "students"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    grade_level: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Attempt(Base):
    __tablename__ = "attempts"
    student_id: Mapped[uuid.UUID]; skill_id: Mapped[uuid.UUID]
    item_ref: Mapped[str]; is_correct: Mapped[bool]; raw_answer: Mapped[str | None]
```

Relevante DDL der anzulegenden Stammdaten (docs/03 §3):

```sql
CREATE TABLE subjects (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  key text UNIQUE NOT NULL,      -- 'math' (Grading-Key, P7)
  name text NOT NULL
);
CREATE TABLE skills (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  subject_id uuid REFERENCES subjects(id),
  key text NOT NULL, name text NOT NULL, grade_level int NOT NULL,
  UNIQUE (subject_id, key)
);
CREATE TABLE skill_edges (
  from_skill uuid REFERENCES skills(id) ON DELETE CASCADE,
  to_skill   uuid REFERENCES skills(id) ON DELETE CASCADE,
  kind text NOT NULL DEFAULT 'prerequisite',
  PRIMARY KEY (from_skill, to_skill, kind)
);
CREATE TABLE classes (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  name text NOT NULL, teacher_id uuid REFERENCES teachers(id)
);
CREATE TABLE enrollments (
  student_id uuid REFERENCES students(id) ON DELETE CASCADE,
  class_id   uuid REFERENCES classes(id)  ON DELETE CASCADE,
  PRIMARY KEY (student_id, class_id)
);
```

Demo-Skill-Graph (analog DB-4, docs/03 §6): `linear-equations → complete-the-square → quadratic-formula` (kind `prerequisite`).

## Umsetzungsschritte

- [ ] `scripts/seed.py` mit dem obigen Gerüst anlegen (argparse-Frontend, `_guard_not_prod`, `seed`).
- [ ] `_guard_not_prod()` implementieren: liest `os.environ.get("DATA_MODE", "mock")`, `sys.exit("REFUSED: ...")` bei `!= "mock"`.
- [ ] Engine/Session über `os.environ["DATABASE_URL"]` aufbauen (privilegierter Dev-User `its`, KEIN `SET ROLE` — der Seeder umgeht RLS bewusst; siehe P1-Kontext).
- [ ] `_ensure_curriculum(s)` idempotent implementieren: Fach `math` über `subjects.key` upserten; Skills (`linear-equations`, `complete-the-square`, `quadratic-formula`) über `(subject_id, key)` upserten; `skill_edges` (prerequisite-Kette) anlegen, ohne bei Re-Run zu duplizieren. Rückgabe: `(subjects, skills)`.
- [ ] `_make_class(s)` implementieren: `Class` mit Namen (z. B. fortlaufend `Klasse {i}`); optional Lehrperson erzeugen/zuordnen.
- [ ] `_make_student(s, klass)` implementieren: `Student` mit `display_name` (synthetisch, kein realer Name) und `grade_level`; `Enrollment(student_id, class_id)` anlegen.
- [ ] Profil-Logik: `empty` → nur Curriculum + `commit`; `demo` → 1 Klasse / 25 Schüler; `load` → `classes` × `students_per_class`.
- [ ] Je Schüler:in `_simulate_history(s, student, skills)` aufrufen (Inhalt in MOCK-2; in MOCK-1 als importierte/aufgerufene Funktion vorsehen).
- [ ] Genau ein abschließendes `s.commit()` (Transaktion zentral steuern).
- [ ] `__main__`-Block: `--reset` ruft `_reset()` (MOCK-3) auf, sonst `seed(...)`.
- [ ] Sicherstellen, dass `_simulate_history` und `_reset` als Symbole existieren (in MOCK-1 ggf. als Stub mit `raise NotImplementedError`/Pass, damit das Skript importierbar/aufrufbar bleibt).

## Akzeptanzkriterien

- [ ] `scripts/seed.py` unterstützt `--profile demo|load|empty` und ist als `uv`-Entrypoint ausführbar.
- [ ] `--profile demo` legt 1 Klasse, ~25 Schüler:innen und das Curriculum an; pro Schüler:in entstehen `attempts` und abgeleiteter `learner_state`.
- [ ] `--profile empty` legt nur Stammdaten (Fächer/Skills/Edges) an, keine Personen.
- [ ] `_ensure_curriculum` ist idempotent: mehrfacher Lauf dupliziert weder Fächer noch Skills noch Edges.
- [ ] `_guard_not_prod()` bricht bei `DATA_MODE != mock` mit `REFUSED:`-Meldung und Exit-Code != 0 ab, BEVOR die DB berührt wird.
- [ ] Keine direkte Manipulation von `learner_state` im Seeder — nur über den Tracing-Service (Vorbereitung MOCK-2).

## Tests / Verifikation

```bash
cd apps/api
# Stammdaten-only, idempotent:
DATA_MODE=mock uv run python ../../scripts/seed.py --profile empty
DATA_MODE=mock uv run python ../../scripts/seed.py --profile empty   # 2. Lauf -> keine Duplikate
# Demo-Datensatz:
DATA_MODE=mock uv run python ../../scripts/seed.py --profile demo
# Guard greift:
DATA_MODE=prod uv run python ../../scripts/seed.py --profile demo    # erwartet: REFUSED..., Exit != 0
```

Erwartete Ergebnisse:
- Nach `--profile empty`: genau 1 `subjects`-Zeile (`math`), 3 `skills`, prerequisite-Edges; 2. Lauf ändert die Zählungen nicht.
- Nach `--profile demo`: 1 `classes`, 25 `students`, 25 `enrollments`, `attempts` > 0, `learner_state` > 0.
- Mit `DATA_MODE=prod`: Ausgabe beginnt mit `REFUSED:`, keine neuen Zeilen in der DB.

> Hinweis: zu entscheiden — ob ein `--seed`-Argument für reproduzierbares RNG ergänzt wird (siehe Epic-Planung, offene Frage 1). MOCK-1 sollte den Parameter zumindest durchreichbar vorsehen.

## Abhängigkeiten

- **DB-2** (SQLAlchemy-Modelle in `db/models.py`): liefert `Student`, `Class`, `Enrollment`, `Subject`, `Skill`, `SkillEdge`, `Attempt`, `LearnerState`, die der Seeder instanziiert.
- **LM-2** (`record_attempt` in `learner_model/tracing.py`): wird aus `_simulate_history` heraus benötigt; MOCK-1 stellt nur den Aufruf-Rahmen, die Lernkurven-Logik kommt in MOCK-2.
- Nachgelagert: **MOCK-2** und **MOCK-3** bauen direkt auf diesem CLI-Gerüst auf; **RET-4** (Population-Tests) konsumiert die später vom `load`-Profil erzeugten Kohorten.

## Definition of Done

- [ ] Akzeptanzkriterien (oben, abgeleitet aus docs/11 A.1) erfüllt.
- [ ] Tests grün; der Guard-Test (`DATA_MODE=prod` verweigert) ist nachgewiesen.
- [ ] Kein LLM betroffen — keine PII in externen Prompts (n/a, aber synthetische `display_name`).
- [ ] `uv`-only; keine `pip`-Aufrufe.
- [ ] GitHub-Issue MOCK-1 geschlossen, Epic-E13-Checkliste aktualisiert.

