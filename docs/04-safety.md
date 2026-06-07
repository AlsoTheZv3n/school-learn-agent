# 04 — Safety & Isolation (E3, M1) · `safety-critical`

> **Das schmerzhaft nachzurüstende Paket — deshalb früh.** Hier wird die Isolation in der
> Datenbank verankert (P1). Selbst eine fehlerhaft generierte Query darf keine fremden Zeilen
> liefern. Min-Cohort verhindert die De-Anonymisierung über Aggregate.

**Voraussetzungen:** DB-3 (`scoped_session` mit Rollen-/`student_id`-Hook).
**Issues:** SAF-1 … SAF-4.

---

## 1. Bedrohungsmodell (knapp)

Ein System, das „erzähl mir über *mich*" **und** „erzähl mir über *alle*" beantwortet, hat
zwei Leck-Flächen zwischen **Personen**:

1. **Individual-Leak:** eine Query, die hätte gescoped sein sollen, liefert fremde Schülerzeilen.
2. **Aggregat-Leak:** eine „Population"-Query über einen Filter, der genau eine Person trifft,
   wird zur de-anonymisierten Einzelauskunft.

Gegenmassnahmen: **RLS** (gegen 1) und **Min-Cohort-Schwelle** (gegen 2). Beide fail-closed.

---

## 2. RLS-Policies (SAF-1)

Als **versionierte Migration** ablegen — RLS ist Schema und muss mit dem Schema migrieren.
`apps/api/src/its/safety/rls.sql` (von einer Alembic-Migration ausgeführt):

```sql
-- Rollen (einmalig; in Migration idempotent via DO-Block)
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='its_student') THEN CREATE ROLE its_student NOLOGIN; END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='its_teacher') THEN CREATE ROLE its_teacher NOLOGIN; END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='its_admin')   THEN CREATE ROLE its_admin   NOLOGIN; END IF;
END $$;

-- Der App-Login-User darf in diese Rollen wechseln (SET ROLE) und liest die Session-Variable.
GRANT its_student, its_teacher, its_admin TO its;

-- Lesezugriff (Tabellen-Grants) — RLS verengt zusätzlich zeilenweise:
GRANT SELECT, INSERT, UPDATE ON attempts, learner_state TO its_student, its_teacher;
GRANT SELECT, INSERT, UPDATE, DELETE ON teacher_notes TO its_teacher;
GRANT SELECT ON enrollments, skills, subjects, skill_edges, content_notes, content_embeddings
  TO its_student, its_teacher;

-- ── RLS auf personenbezogenen Tabellen aktivieren ──
ALTER TABLE attempts        ENABLE ROW LEVEL SECURITY;
ALTER TABLE learner_state   ENABLE ROW LEVEL SECURITY;
ALTER TABLE teacher_notes   ENABLE ROW LEVEL SECURITY;
ALTER TABLE enrollments     ENABLE ROW LEVEL SECURITY;

-- Hilfsausdruck: aktuelle Schüler-ID aus Session-Variable (NULL wenn nicht gesetzt → fail-closed)
-- current_setting('app.current_student_id', true) liefert NULL statt Fehler, wenn ungesetzt.

-- STUDENT: sieht ausschliesslich eigene Zeilen
CREATE POLICY student_attempts_self ON attempts
  FOR ALL TO its_student
  USING (student_id = NULLIF(current_setting('app.current_student_id', true), '')::uuid)
  WITH CHECK (student_id = NULLIF(current_setting('app.current_student_id', true), '')::uuid);

CREATE POLICY student_state_self ON learner_state
  FOR ALL TO its_student
  USING (student_id = NULLIF(current_setting('app.current_student_id', true), '')::uuid)
  WITH CHECK (student_id = NULLIF(current_setting('app.current_student_id', true), '')::uuid);

-- Schüler dürfen Lehrernotizen über sich LESEN (z. B. „Note from Frau Meier")
CREATE POLICY student_notes_about_self ON teacher_notes
  FOR SELECT TO its_student
  USING (student_id = NULLIF(current_setting('app.current_student_id', true), '')::uuid);

CREATE POLICY student_enrollment_self ON enrollments
  FOR SELECT TO its_student
  USING (student_id = NULLIF(current_setting('app.current_student_id', true), '')::uuid);

-- TEACHER: sieht Zeilen der Schüler:innen in seinen/ihren Klassen
-- (Lehrer-Identität via separate Session-Variable app.current_teacher_id)
CREATE POLICY teacher_attempts_in_class ON attempts
  FOR SELECT TO its_teacher
  USING (student_id IN (
    SELECT e.student_id FROM enrollments e
    JOIN classes c ON c.id = e.class_id
    WHERE c.teacher_id = NULLIF(current_setting('app.current_teacher_id', true), '')::uuid
  ));

CREATE POLICY teacher_state_in_class ON learner_state
  FOR SELECT TO its_teacher
  USING (student_id IN (
    SELECT e.student_id FROM enrollments e
    JOIN classes c ON c.id = e.class_id
    WHERE c.teacher_id = NULLIF(current_setting('app.current_teacher_id', true), '')::uuid
  ));

CREATE POLICY teacher_notes_rw ON teacher_notes
  FOR ALL TO its_teacher
  USING (teacher_id = NULLIF(current_setting('app.current_teacher_id', true), '')::uuid)
  WITH CHECK (teacher_id = NULLIF(current_setting('app.current_teacher_id', true), '')::uuid);

-- ADMIN: BYPASSRLS bewusst NICHT pauschal. Admin-Funktionen laufen über dedizierte,
-- geprüfte Pfade. (Wenn nötig, gezielt einzelne Policies FOR ALL TO its_admin USING (true).)
```

> Ergänze `scoped_session` (DB-3) so, dass für `TEACHER` zusätzlich
> `SET app.current_teacher_id = :tid` gesetzt wird (analog zur Schüler-Variable).

**Warum `current_setting(..., true)` + `NULLIF`:** Ist die Variable nicht gesetzt, ergibt der
Ausdruck `NULL`; `student_id = NULL` ist niemals wahr → **fail-closed** (keine Zeilen statt aller Zeilen).

---

## 3. Scoping-Resolver (SAF-2)

`apps/api/src/its/safety/scoping.py`:

```python
from its.auth.deps import Principal
from its.auth.roles import Role

class ScopeError(PermissionError):
    pass

def require_student_scope(principal: Principal) -> str:
    """Gibt die student_id zurück, auf die eine Individual-Query zwingend gescoped wird.
    Fail-closed: kein Scope -> ScopeError, niemals 'alle'."""
    if principal.role == Role.STUDENT:
        if not principal.student_id:
            raise ScopeError("student without student_id")
        return principal.student_id
    raise ScopeError("individual query requires a student-scoped principal")

def teacher_id_of(principal: Principal) -> str:
    if principal.role != Role.TEACHER:
        raise ScopeError("not a teacher principal")
    return principal.user_id
```

**AK:** Es gibt keinen Codepfad, der eine Individual-Query *ohne* aufgelösten Scope ausführt;
fehlender Scope wirft `ScopeError`.

---

## 4. Min-Cohort-Schwelle (SAF-3)

`apps/api/src/its/safety/cohort.py`:

```python
from dataclasses import dataclass
from its.config import settings

class CohortTooSmall(PermissionError):
    pass

@dataclass(frozen=True)
class CohortResult:
    n: int
    payload: dict

def enforce_min_cohort(n: int, payload: dict, k: int | None = None) -> CohortResult:
    """Verweigert Aggregate, deren Gruppe kleiner als k ist (Default aus settings.min_cohort_k).
    JEDE Population-Query MUSS hierdurch laufen, bevor ein Resultat das System verlässt."""
    threshold = k if k is not None else settings.min_cohort_k
    if n < threshold:
        raise CohortTooSmall(f"cohort n={n} below threshold k={threshold}")
    return CohortResult(n=n, payload=payload)
```

**AK:** Aggregate mit `n < k` werfen `CohortTooSmall`; Default `k=10` über `settings`; eine
zentrale Stelle, durch die jede Aggregat-Antwort geht.

---

## 5. Safety-Tests (SAF-4) · **CI-blockierend**

Die zwei Eigenschaften, deren stiller Bruch Kinderdaten leakt. Detaillierte Fixtures in docs/10.

`tests/test_rls.py` (Kernidee):

```python
def test_student_cannot_read_other_students_attempts(db_factory, two_students):
    a, b = two_students
    # Session als Schüler A
    with db_factory.as_student(a.id) as s:
        rows = s.execute(text("SELECT count(*) FROM attempts WHERE student_id = :b"),
                         {"b": str(b.id)}).scalar()
        assert rows == 0           # A sieht KEINE Zeilen von B
    # Gegenprobe: A sieht eigene
    with db_factory.as_student(a.id) as s:
        own = s.execute(text("SELECT count(*) FROM attempts")).scalar()
        assert own > 0

def test_unset_scope_returns_no_rows(db_factory):
    # Schüler-Rolle ohne gesetzte student_id -> fail-closed
    with db_factory.as_student(student_id=None, allow_unscoped=True) as s:
        n = s.execute(text("SELECT count(*) FROM attempts")).scalar()
        assert n == 0
```

`tests/test_cohort_threshold.py`:

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

**AK:** Beide Testdateien laufen in CI und **blockieren den Merge** bei Fehlschlag.

---

## 6. Akzeptanzkriterien (gesamt)

- [ ] `rls.sql` als Migration; RLS auf `attempts`, `learner_state`, `teacher_notes`, `enrollments` (SAF-1)
- [ ] Rollen `its_student/teacher/admin`; Schüler-Policy fail-closed via `current_setting` (SAF-1)
- [ ] `scoping.py`: keine ungescopte Individual-Query möglich (SAF-2)
- [ ] `cohort.py`: zentrale Min-Cohort-Durchsetzung, Default `k=10` (SAF-3)
- [ ] `test_rls.py` + `test_cohort_threshold.py` grün und CI-blockierend (SAF-4)
- [ ] `scoped_session` setzt zusätzlich `app.current_teacher_id` für Lehrer

---

## Claude-Code-Prompt

```
Setze E3 (docs/04-safety.md) um — höchste Priorität. Erzeuge safety/rls.sql und führe es als
Alembic-Migration aus (Rollen, Grants, RLS-Policies, fail-closed via current_setting+NULLIF).
Ergänze db/session.py um app.current_teacher_id für Lehrer. Implementiere safety/scoping.py
(require_student_scope, fail-closed) und safety/cohort.py (enforce_min_cohort, Default k aus
settings). Schreibe tests/test_rls.py und tests/test_cohort_threshold.py und stelle sicher,
dass CI bei Fehlschlag blockiert. Beweise mit den Tests: Schüler A kann Zeilen von B nicht
lesen, ungescopte Schüler-Session liefert 0 Zeilen, Kohorte < k wird verweigert. Schliesse SAF-1..4.
```
