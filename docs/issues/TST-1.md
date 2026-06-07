## Ziel

`tests/conftest.py` stellt eine **transaktionale Test-DB-Fixture** (jeder Test in eigener Transaktion, am Ende Rollback) und eine **`DBFactory`** bereit, die Sessions in den Postgres-Rollen `its_student`/`its_teacher`/`its_admin` öffnet (fail-closed). Migrationen **inklusive `rls.sql`** werden via Alembic `upgrade head` gegen die Test-DB angewandt. Damit laufen die Safety-Tests (SAF-4) sowie TST-3/TST-4 gegen echtes Postgres mit aktivierter RLS.

## Kontext & Prinzipien

- **P1 (Safety zuerst, in der DB verankert):** Die Fixtures müssen gegen **echtes Postgres mit aktivierter RLS** laufen — gegen SQLite würde die wichtigste Eigenschaft (Zeilenisolation) gar nicht geprüft. Deshalb `create_engine(DATABASE_URL)` auf einen pgvector-Service und `command.upgrade(cfg, "head")`, das die `rls.sql`-Migration mitzieht.
- **P1 / fail-closed:** Die `DBFactory` ist ein **Test-Spiegel** von `scoped_session` (DB-3). Sie setzt `SET ROLE` und `SET app.current_student_id` exakt wie der Produktionscode, damit die Tests genau den Rollen-/Variablen-Mechanismus prüfen, auf dem die RLS-Policies beruhen. Schüler-Session ohne `student_id` (und ohne `allow_unscoped`) wirft `PermissionError` — fail-closed.
- **P9 (`uv` ausschliesslich):** Alle Testläufe über `uv run pytest`, niemals `pip`.

## Zu erstellende/ändernde Dateien

- `tests/conftest.py` — neu (Fixtures: `engine`, `db`, `db_factory`, `two_students`, `DBFactory`).
- `apps/api/alembic.ini` + `apps/api/.../env.py` — vorhanden vorausgesetzt (DB-1); die `engine`-Fixture ruft `command.upgrade(Config("alembic.ini"), "head")`.
- `.github/workflows/ci.yml` — bestehender Workflow (FND-6); wird in TST für das Safety-Gate erweitert (siehe docs/10 §7, hier nur Vorbereitung der Fixture).

> Hinweis: zu entscheiden — die in docs/10 §5 von TST-3 referenzierte Fixture `seeded_student_and_item` und die zugehörige `load_item`/`content/items.py` sind nirgends spezifiziert. Sie sollten hier (oder als Vorbedingung) ergänzt werden, sonst kann TST-3 nicht laufen.

## Schnittstellen & Signaturen

`tests/conftest.py` (aus docs/10 §2, autark reproduziert):

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

Referenz: der Produktions-Hook, den die `DBFactory` spiegelt (`apps/api/src/its/db/session.py`, DB-3):

```python
@contextmanager
def scoped_session(principal: Principal) -> Iterator[Session]:
    session = SessionLocal()
    try:
        pg_role = PG_ROLE[principal.role]
        session.execute(text("SET ROLE :r").bindparams(r=pg_role))
        if principal.role == Role.STUDENT:
            if not principal.student_id:
                raise PermissionError("student principal without student_id (fail-closed)")
            session.execute(text("SET app.current_student_id = :sid").bindparams(sid=principal.student_id))
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.execute(text("RESET ROLE"))
        session.close()
```

RLS-relevant: die Policies lesen `NULLIF(current_setting('app.current_student_id', true), '')::uuid` (docs/04 §2) — ungesetzt ⇒ NULL ⇒ keine Zeilen (fail-closed). Die Rollen `its_student/its_teacher/its_admin` und das Recht des App-Users, in sie zu wechseln, kommen aus `rls.sql`.

## Umsetzungsschritte

- [ ] `tests/conftest.py` anlegen; `DATABASE_URL` aus der Umgebung lesen (kein Default auf SQLite).
- [ ] **Guard:** wenn `DATABASE_URL` fehlt oder nicht auf Postgres zeigt, mit klarer Meldung abbrechen (verhindert versehentliches Testen ohne RLS).
- [ ] `engine`-Fixture (`scope="session"`): Engine bauen, `Config("alembic.ini")` laden, `command.upgrade(cfg, "head")` → Schema **inkl. `rls.sql`-Migration** anwenden; am Ende `eng.dispose()`.
- [ ] Sicherstellen, dass die Alembic-`env.py` `settings.database_url`/`DATABASE_URL` und `Base.metadata` nutzt (DB-1) — sync-Variante bevorzugen.
- [ ] `db`-Fixture: Connection + äussere Transaktion + Session; `finally` → `session.close()`, `trans.rollback()`, `conn.close()`.
- [ ] `DBFactory` mit `_as(...)`, `as_student`, `as_teacher`, `as_admin` implementieren; `SET ROLE`, `SET app.current_student_id`, `SET app.current_teacher_id`; `RESET ROLE` im `finally`.
- [ ] **Fail-closed-Check:** `its_student` + `student_id is None` + `allow_unscoped=False` ⇒ `PermissionError`.
- [ ] `db_factory`- und `two_students`-Fixture bereitstellen (zwei Schüler + Skill + je 1 Attempt via `flush`, ohne `commit`).
- [ ] **(Zusatz, falls TST-3 hier verortet)** `seeded_student_and_item`-Fixture entwerfen: Schüler + Skill + kuratiertes Item (`item_ref`, `answer_key`) so, dass der Math-Grader es bewerten kann.
- [ ] Lokal verifizieren, dass `two_students` + `db` korrekt rollbacken (keine Reststände zwischen Tests).

## Akzeptanzkriterien

- [ ] `conftest.py`: transaktionale Test-DB-Fixture (`db`) — jeder Test isoliert, am Ende Rollback.
- [ ] `DBFactory` mit `as_student`/`as_teacher`/`as_admin` vorhanden; setzt Rolle + `app.current_student_id`/`app.current_teacher_id`.
- [ ] **Fail-closed:** Schüler-Session ohne `student_id` (und ohne `allow_unscoped`) wirft `PermissionError`.
- [ ] Migrationen **inkl. `rls.sql`** werden via `command.upgrade(cfg, "head")` gegen die Test-DB angewandt.
- [ ] `two_students`-Fixture legt zwei Schüler + Skill + je 1 Attempt an.
- [ ] Fixtures laufen gegen **echtes Postgres mit RLS**, nicht SQLite.

## Tests / Verifikation

```bash
# DB hochfahren
docker compose -f infra/docker-compose.yml up -d
# Umgebung
export DATABASE_URL=postgresql+psycopg://its:its_dev_pw@localhost:5432/its
cd apps/api && uv sync
# Smoke: die Fixtures müssen vom Safety-Test konsumierbar sein
uv run pytest tests/test_rls.py tests/test_cohort_threshold.py -q
```

Erwartet: Die Safety-Tests sammeln (collecten) ohne Fixture-Fehler und laufen grün. Ein gezielter Probe-Test, der `db_factory.as_student(student_id=None, allow_unscoped=False)` öffnet, muss `PermissionError` werfen. Ein Test, der nach `two_students` in einer neuen `db`-Fixture läuft, darf die im Vortest angelegten Zeilen **nicht** sehen (Rollback-Isolation belegt).

## Abhängigkeiten

- **FND-6 (CI-Grundgerüst):** liefert `ci.yml` mit Postgres-Service; E12 erweitert ihn um das Safety-Gate. Ohne CI kein blockierender Lauf.
- **DB-3 (`scoped_session`):** Die `DBFactory` spiegelt diesen Rollen-/`student_id`-Hook — ohne ihn fehlt die Vorlage für den Test-Mechanismus.
- **Nachgelagert:** SAF-4 (`test_rls.py`, `test_cohort_threshold.py`) sowie **TST-3** (Agent-Turn) und **TST-4** (E2E-Smoke) bauen alle auf diesen Fixtures auf.

## Definition of Done

- [ ] Akzeptanzkriterien aus docs/10 §8 (Fixture-Teil) erfüllt: transaktionale Test-DB + `DBFactory`; Migrationen inkl. `rls.sql` angewandt.
- [ ] Tests grün, inkl. der Safety-Tests, die auf diesen Fixtures laufen.
- [ ] Keine PII in externen LLM-Prompts — für diesen Task nicht zutreffend (kein LLM-Pfad).
- [ ] `uv`-only, keine `pip`-Aufrufe.
- [ ] Zugehöriges GitHub-Issue (TST-1) geschlossen, Epic-Checkliste (E12) aktualisiert.
