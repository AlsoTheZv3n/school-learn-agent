## Ziel

Automatisierte, **CI-blockierende** Tests beweisen die zwei Safety-Eigenschaften, deren stiller Bruch Kinderdaten leakt: (1) Zeilenisolation via RLS — Schueler A sieht keine Zeilen von B, eine ungescopte Schueler-Session liefert 0 Zeilen; (2) Min-Cohort — eine Kohorte < `k` wird verweigert. Die Tests laufen gegen echtes Postgres mit aktivierter RLS und blockieren den Merge bei Fehlschlag.

## Kontext & Prinzipien

- **P1 (Safety zuerst, in der DB verankert):** Diese Tests sind der Beweis, dass P1 haelt. Sie sind nicht verhandelbar und blockieren den Merge — eine gebrochene Isolationsgarantie darf niemals stillschweigend gemergt werden.
- **P8 (Schutz Minderjaehriger / Residenz):** Der Bruch genau dieser zwei Eigenschaften bedeutet ein DSG/DSGVO-Datenleck ueber Kinder. Der CI-Gate ist die kontinuierliche Absicherung.
- **P5/P6 (Open Learner Model / Mensch im Loop):** Die Teacher-Sichtbarkeit (nur eigene Klassen) und die Aggregat-Schutzschwelle sind Teil der menschlichen Aufsicht; ihre Korrektheit wird hier mitgesichert.

## Zu erstellende/aendernde Dateien

- `tests/test_rls.py` — RLS-Isolationstests (Repo-Layout Section 6: `tests/ # inkl. test_rls.py, test_cohort_threshold.py (CI-blockierend)`).
- `tests/test_cohort_threshold.py` — Min-Cohort-Tests.
- `.github/workflows/ci.yml` — vorgelagerter, blockierender Safety-Schritt vor der vollen Suite.
- `tests/conftest.py` — Fixtures `db_factory` und `two_students` (formal TST-1; fuer SAF-4 noetig — entweder hier mitliefern oder als harte Abhaengigkeit deklarieren).

## Schnittstellen & Signaturen

`tests/test_rls.py` (Kernidee, docs/04 §5):

```python
from sqlalchemy import text

def test_student_cannot_read_other_students_attempts(db_factory, two_students):
    a, b = two_students
    with db_factory.as_student(a.id) as s:
        rows = s.execute(text("SELECT count(*) FROM attempts WHERE student_id = :b"),
                         {"b": str(b.id)}).scalar()
        assert rows == 0           # A sieht KEINE Zeilen von B
    with db_factory.as_student(a.id) as s:
        own = s.execute(text("SELECT count(*) FROM attempts")).scalar()
        assert own > 0             # Gegenprobe: A sieht eigene

def test_unset_scope_returns_no_rows(db_factory):
    with db_factory.as_student(student_id=None, allow_unscoped=True) as s:
        n = s.execute(text("SELECT count(*) FROM attempts")).scalar()
        assert n == 0              # fail-closed
```

`tests/test_cohort_threshold.py` (docs/04 §5):

```python
import pytest
from its.safety.cohort import enforce_min_cohort, CohortTooSmall

def test_small_cohort_refused():
    with pytest.raises(CohortTooSmall):
        enforce_min_cohort(n=3, payload={"avg": 0.7}, k=10)

def test_sufficient_cohort_ok():
    res = enforce_min_cohort(n=25, payload={"avg": 0.7}, k=10)
    assert res.n == 25 and res.payload["avg"] == 0.7
```

Benoetigte Fixtures (docs/10 §2) — `DBFactory` spiegelt `scoped_session`:

```python
class DBFactory:
    @contextmanager
    def _as(self, pg_role, *, student_id=None, teacher_id=None, allow_unscoped=False):
        SessionLocal = sessionmaker(bind=self._engine, expire_on_commit=False)
        s = SessionLocal()
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
            s.execute(text("RESET ROLE")); s.close()
    def as_student(self, student_id=None, allow_unscoped=False): ...
    def as_teacher(self, teacher_id): ...
    def as_admin(self): ...

@pytest.fixture
def two_students(db):
    """Legt zwei Schueler mit je einem attempt an (Setup ueber Owner-/Admin-Pfad)."""
    from its.db.models import Student, Skill, Attempt
    a = Student(id=uuid.uuid4(), display_name="A", grade_level=9)
    b = Student(id=uuid.uuid4(), display_name="B", grade_level=9)
    skill = Skill(id=uuid.uuid4(), subject_id=None, key="demo", name="Demo", grade_level=9)
    db.add_all([a, b, skill]); db.flush()
    db.add_all([
        Attempt(student_id=a.id, skill_id=skill.id, item_ref="i1", is_correct=True),
        Attempt(student_id=b.id, skill_id=skill.id, item_ref="i1", is_correct=False),
    ]); db.flush()
    return a, b
```

CI-Erweiterung (docs/10 §7) — vorgelagerter, blockierender Schritt:

```yaml
      - name: Safety gate (blocking)
        working-directory: apps/api
        run: uv run pytest tests/test_rls.py tests/test_cohort_threshold.py -q

      - name: Full test suite
        working-directory: apps/api
        run: uv run pytest -q
```

## Umsetzungsschritte

- [ ] Sicherstellen, dass `conftest.py` die Fixtures `engine` (Alembic `upgrade head` inkl. `rls.sql` gegen die Test-DB), `db`, `db_factory`, `two_students` bereitstellt (docs/10 §2). Falls TST-1 noch nicht vorliegt: minimale Variante hier mitliefern.
- [ ] `tests/test_rls.py` mit den drei Faellen schreiben: (a) A sieht 0 Zeilen von B in `attempts`; (b) A sieht eigene Zeilen (>0); (c) Schueler-Session ohne `student_id` (`allow_unscoped=True`) → 0 Zeilen.
- [ ] Empfohlen: denselben Isolationstest fuer `learner_state` ergaenzen (docs/10 §3 nennt `attempts` und `learner_state`).
- [ ] `tests/test_cohort_threshold.py` mit `test_small_cohort_refused` und `test_sufficient_cohort_ok` schreiben.
- [ ] `ci.yml` um einen **vorgelagerten** `Safety gate (blocking)`-Schritt erweitern, der vor der vollen Suite laeuft (`tests/test_rls.py tests/test_cohort_threshold.py`).
- [ ] Pruefen, dass die Tests gegen **echtes Postgres** laufen (pgvector-Service aus FND-6), nicht gegen SQLite — sonst wird RLS gar nicht geprueft.
- [ ] Pruefen, dass die Daten-Setup-Schreibpfade (`two_students`) RLS nicht aushebeln und die Lese-Assertions strikt ueber `db_factory.as_student` laufen.

> Hinweis: zu entscheiden — ob `conftest.py` (TST-1) als harte Vorbedingung von SAF-4 deklariert oder die Fixtures hier minimal mitgeliefert werden. Empfehlung: minimal mitliefern und spaeter in TST-1 konsolidieren, damit das Safety-Gate nicht auf E12 wartet.

## Akzeptanzkriterien

- [ ] `tests/test_rls.py` und `tests/test_cohort_threshold.py` existieren und laufen gruen gegen echtes Postgres mit aktivierter RLS.
- [ ] Beweis Zeilenisolation: Schueler A sieht 0 Zeilen von B (mind. `attempts`); A sieht eigene Zeilen (>0).
- [ ] Beweis fail-closed: Schueler-Session ohne `student_id` liefert 0 Zeilen.
- [ ] Beweis Min-Cohort: `n < k` → `CohortTooSmall`; `n >= k` → Payload durch.
- [ ] Die Safety-Tests laufen als **vorgelagerter, blockierender** CI-Schritt und koennen nicht uebersprungen werden; bei Fehlschlag blockiert der Merge.

## Tests / Verifikation

```bash
# DB hochfahren und Migrationen inkl. rls.sql anwenden
docker compose -f infra/docker-compose.yml up -d
cd apps/api && uv run alembic upgrade head

# Nur das Safety-Gate (so wie CI es vorgelagert ausfuehrt)
uv run pytest tests/test_rls.py tests/test_cohort_threshold.py -q

# Volle Suite
uv run pytest -q
```

Erwartete Ergebnisse: Das Safety-Gate meldet alle Faelle gruen. Wird die RLS in der Migration deaktiviert oder die Cohort-Schwelle aufgeweicht, schlagen die Tests rot fehl und blockieren den Merge.

## Abhaengigkeiten

- **SAF-1** — ohne aktive RLS-Policies haetten die Isolationstests nichts zu pruefen (bzw. wuerden faelschlich gruen sein, falls Daten sichtbar bleiben).
- **SAF-2** — der Scoping-Resolver gehoert zur abgesicherten Oberflaeche; SAF-4 sichert das fail-closed-Verhalten der Schueler-Session mit.
- **SAF-3** — `enforce_min_cohort` wird direkt von `test_cohort_threshold.py` importiert und geprueft.
- Konsumiert **FND-6** (CI-Workflow + Postgres-Service) und **DB-3** (`scoped_session`/Schema); benoetigt die `conftest.py`-Fixtures (TST-1).
- Nachgelagert: schaltet das Safety-Gate scharf, das alle weiteren M1+-Pakete (RET-3/4, API-2/3) absichert.

## Definition of Done

- [ ] Akzeptanzkriterien aus docs/04 §5 erfuellt (beide Testdateien gruen und CI-blockierend).
- [ ] Tests gruen, inkl. der Safety-Tests (das ist hier der Kerninhalt).
- [ ] Kein PII in externen LLM-Prompts (nicht betroffen; reine Testschicht).
- [ ] `uv`-only — Tests laufen via `uv run pytest`, keine `pip`-Aufrufe.
- [ ] Zugehoeriges GitHub-Issue SAF-4 geschlossen, E3-Epic-Checkliste aktualisiert.
