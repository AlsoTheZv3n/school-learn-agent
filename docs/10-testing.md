# 10 — Testing & CI (E12, kontinuierlich · Abschluss M6)

**Ziel:** Eine Teststrategie, die die Safety-Eigenschaften absichert (CI-blockierend) und die
Kernlogik (Lernmodell, Grading, Agent-Loop, API) abdeckt. Die eigentlichen Safety-Tests sind in
[`docs/04`](04-safety.md) spezifiziert — hier kommen die **Fixtures** dafür und die übrige Pyramide.

**Voraussetzungen:** FND-6 (CI), DB-3 (`scoped_session`), die jeweiligen Feature-Pakete.
**Issues:** TST-1 … TST-4.

---

## 1. Teststrategie (Pyramide)

| Ebene | Was | Gegen was |
|---|---|---|
| **Safety** (kritisch) | RLS-Isolation, Min-Cohort | echte Postgres-DB mit RLS |
| **Unit** | BKT, Grader, Parser, Anonymizer | reine Funktionen, keine DB |
| **Integration** | Agent-Loop (ein voller Turn), Tracing-Schreibpfad | Test-DB |
| **E2E-Smoke** | Login → Session → Antwort → Mastery; Lehrer sieht Stand | API (+ Frontend) |

Grundsätze:
- Die **Safety-Tests** (`test_rls.py`, `test_cohort_threshold.py`) sind nicht verhandelbar und
  **blockieren den Merge** (P1).
- Tests laufen gegen **echtes Postgres mit aktivierter RLS** — gegen SQLite o. Ä. würde die
  wichtigste Eigenschaft (Zeilenisolation) gar nicht geprüft.
- Unit-Tests der reinen Logik (BKT/Grader) brauchen **keine** DB und laufen schnell.

---

## 2. Pytest-Fixtures (TST-1)

`tests/conftest.py` — transaktionale Test-DB + Rollen-Fabrik:

```python
import os
import uuid
import pytest
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

TEST_DB_URL = os.environ["DATABASE_URL"]   # in CI: Postgres-Service mit pgvector

@pytest.fixture(scope="session")
def engine():
    eng = create_engine(TEST_DB_URL, pool_pre_ping=True)
    # Migrationen + rls.sql gegen die Test-DB anwenden (Alembic upgrade head)
    from alembic.config import Config
    from alembic import command
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
    yield eng
    eng.dispose()

@pytest.fixture
def db(engine):
    """Jeder Test in einer Transaktion, am Ende Rollback -> isolierte Tests."""
    conn = engine.connect()
    trans = conn.begin()
    SessionLocal = sessionmaker(bind=conn, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        conn.close()

class DBFactory:
    """Öffnet Sessions in einer bestimmten Rolle — spiegelt scoped_session (docs/03)."""
    def __init__(self, engine):
        self._engine = engine

    @contextmanager
    def _as(self, pg_role: str, *, student_id=None, teacher_id=None, allow_unscoped=False):
        SessionLocal = sessionmaker(bind=self._engine, expire_on_commit=False)
        s: Session = SessionLocal()
        try:
            s.execute(text("SET ROLE :r").bindparams(r=pg_role))
            if pg_role == "its_student" and student_id is None and not allow_unscoped:
                raise PermissionError("student session requires student_id")
            if student_id is not None:
                s.execute(text("SET app.current_student_id = :v").bindparams(v=str(student_id)))
            if teacher_id is not None:
                s.execute(text("SET app.current_teacher_id = :v").bindparams(v=str(teacher_id)))
            yield s
        finally:
            s.execute(text("RESET ROLE"))
            s.close()

    def as_student(self, student_id=None, allow_unscoped=False):
        return self._as("its_student", student_id=student_id, allow_unscoped=allow_unscoped)
    def as_teacher(self, teacher_id):
        return self._as("its_teacher", teacher_id=teacher_id)
    def as_admin(self):
        return self._as("its_admin")

@pytest.fixture
def db_factory(engine) -> DBFactory:
    return DBFactory(engine)

@pytest.fixture
def two_students(db):
    """Legt zwei Schüler mit je einem attempt an (als Setup über Admin/Owner-Pfad)."""
    from its.db.models import Student, Skill, Attempt
    a = Student(id=uuid.uuid4(), display_name="A", grade_level=9)
    b = Student(id=uuid.uuid4(), display_name="B", grade_level=9)
    skill = Skill(id=uuid.uuid4(), subject_id=None, key="demo", name="Demo", grade_level=9)
    db.add_all([a, b, skill])
    db.flush()
    db.add_all([
        Attempt(student_id=a.id, skill_id=skill.id, item_ref="i1", is_correct=True),
        Attempt(student_id=b.id, skill_id=skill.id, item_ref="i1", is_correct=False),
    ])
    db.flush()
    return a, b
```

> Die `DBFactory` ist bewusst ein **Test-Spiegel** von `scoped_session` — damit die Tests
> exakt den Rollen-/Variablen-Mechanismus prüfen, auf dem die RLS-Policies beruhen.

---

## 3. Safety-Tests (in `docs/04` spezifiziert, hier verortet)

`tests/test_rls.py` und `tests/test_cohort_threshold.py` nutzen `db_factory`/`two_students` aus
§2. Inhaltlich siehe [`docs/04` §5](04-safety.md). Sie sind Teil von **TST** und **CI-blockierend**.

Mindestfälle:
- Schüler A sieht **0** Zeilen von B (`attempts`, `learner_state`).
- Schüler A sieht die **eigenen** Zeilen (> 0) — Gegenprobe.
- Schüler-Session **ohne** `student_id` → **0** Zeilen (fail-closed).
- `enforce_min_cohort(n<k)` → `CohortTooSmall`; `n>=k` → Payload durch.

---

## 4. Unit-Tests Lernmodell & Grading (TST-2)

`tests/test_bkt.py`:

```python
from its.learner_model.bkt import posterior, update, mastery_after, BKTParams

def test_posterior_in_range():
    p = BKTParams()
    assert 0.0 <= posterior(0.3, True, p) <= 1.0
    assert 0.0 <= posterior(0.3, False, p) <= 1.0

def test_correct_increases_mastery():
    p = BKTParams()
    assert mastery_after([True, True, True], p) > mastery_after([True], p)

def test_wrong_does_not_exceed_correct():
    p = BKTParams()
    assert mastery_after([False, False], p) < mastery_after([True, True], p)
```

`tests/test_grading/test_math.py`:

```python
from its.grading.math import MathGrader
from its.grading.base import Item

def test_math_equivalent_forms_accepted():
    g = MathGrader()
    item = Item(skill_key="expand", prompt="(x+1)^2", answer_key="x**2 + 2*x + 1")
    assert g.grade("x^2+2*x+1", item).correct is True

def test_math_wrong_rejected():
    g = MathGrader()
    item = Item(skill_key="expand", prompt="(x+1)^2", answer_key="x**2 + 2*x + 1")
    res = g.grade("x^2+1", item)
    assert res.correct is False and res.confidence == 1.0
```

Zusätzlich: `tests/test_content_parser.py` (Prosa/Code-Trennung, Wikilink-Extraktion) und
`tests/test_anonymize.py` (Name/Datum/E-Mail werden ersetzt, P4).

---

## 5. Integrationstest Agent-Loop (TST-3)

`tests/test_agent_turn.py` — ein vollständiger `ANSWER`-Turn end-to-end gegen die Test-DB:

```python
def test_answer_turn_updates_mastery(db_factory, seeded_student_and_item):
    student, item_ref, skill_key = seeded_student_and_item
    from its.agent.graph import build_graph
    from its.agent.state import TutorState, Intent
    graph = build_graph()
    with db_factory.as_student(student.id):
        state = TutorState(student_id=str(student.id), subject_key="math",
                           skill_key=skill_key, intent=Intent.ANSWER,
                           answer="x**2 + 2*x + 1", item_ref=item_ref)
        result = graph.invoke(state)
    assert result.grade is not None
    assert result.grade["confidence"] == 1.0     # kuratiert (P2)
    assert result.mastery is not None            # Modell wurde aktualisiert (P3)
```

> Prüft die Prinzipien operativ: `assess` ist deterministisch (Konfidenz 1.0), und das
> **Learner-Modell** ändert sich — nicht der Agent.

---

## 6. E2E-Smoke (TST-4)

`tests/e2e/` — Login → Session → Antwort → Mastery sichtbar; danach Lehrer-Sicht. Zwei Varianten je
nach Reifegrad:
- **HTTP-Smoke** (schnell, ohne Browser): `httpx`-Client gegen die laufende API; Token für
  Schüler/Lehrer; ruft `/student/turn`, dann `/student/mastery`, dann als Lehrer
  `/teacher/student/{id}/mastery` und erwartet konsistente Werte (Lehrer sieht zusätzlich
  `uncertainty`).
- **Browser-E2E** (Playwright): Schüler beantwortet eine Aufgabe, sieht die Mastery-Bar steigen;
  Lehrer öffnet das Panel und sieht den Stand inkl. Unsicherheit; kleine Kohorte zeigt den
  „zu wenige Lernende"-Hinweis statt Zahlen.

---

## 7. CI-Integration

`ci.yml` (aus FND-6) wird so erweitert, dass die Safety-Tests **nicht** übersprungen werden
können. Empfehlung:

```yaml
      - name: Safety gate (blocking)
        working-directory: apps/api
        run: uv run pytest tests/test_rls.py tests/test_cohort_threshold.py -q

      - name: Full test suite
        working-directory: apps/api
        run: uv run pytest -q
```

> Ein separater, **vorgelagerter** Safety-Schritt macht im CI-Log sofort sichtbar, wenn die
> Isolationsgarantien brechen — noch bevor die übrige Suite läuft.

---

## 8. Akzeptanzkriterien (gesamt)

- [ ] `conftest.py`: transaktionale Test-DB + `DBFactory` (student/teacher/admin) (TST-1)
- [ ] Migrationen **inkl. `rls.sql`** werden gegen die Test-DB angewandt (TST-1)
- [ ] BKT- und Grading-Unit-Tests grün; Parser/Anonymizer getestet (TST-2)
- [ ] Agent-Turn-Integrationstest: Konfidenz 1.0 + Mastery aktualisiert (TST-3)
- [ ] E2E-Smoke (HTTP mindestens) grün (TST-4)
- [ ] Safety-Tests laufen als vorgelagerter, blockierender CI-Schritt

---

## Claude-Code-Prompt

```
Setze E12 (docs/10-testing.md) um: tests/conftest.py mit transaktionaler Test-DB-Fixture und
DBFactory (as_student/as_teacher/as_admin, fail-closed), wobei Alembic inkl. rls.sql gegen die
Test-DB angewandt wird. Implementiere die Unit-Tests (test_bkt.py, test_grading/, test_content_parser.py,
test_anonymize.py), den Agent-Integrationstest (test_agent_turn.py: Konfidenz 1.0 + Mastery
aktualisiert) und einen HTTP-E2E-Smoke. Erweitere ci.yml um einen vorgelagerten, blockierenden
Safety-Schritt (test_rls.py + test_cohort_threshold.py) vor der vollen Suite. Stelle sicher, dass
die Safety-Tests aus docs/04 hier mit den Fixtures laufen. Schliesse TST-1..4.
```
