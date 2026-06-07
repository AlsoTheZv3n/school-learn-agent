## Ziel

Engine-/Session-Setup in `db/session.py` mit `scoped_session(principal)`: ein Context-Manager, der pro Request die **Postgres-Rolle** setzt und für Schüler:innen die **`student_id` als Session-Variable** (`app.current_student_id`) hinterlegt. Ohne aufgelösten Scope wird **fail-closed** abgebrochen (`PermissionError`). Dieser Hook ist die Brücke zu den RLS-Policies (E3).

## Kontext & Prinzipien

- **P1 (Safety zuerst, in der DB verankert) — `safety-critical`:** Dieser Hook ist die App-seitige Hälfte der Isolation. Die DB-seitige Hälfte (RLS) liest die hier gesetzte Session-Variable `app.current_student_id`. Selbst eine fehlerhafte Query darf später keine fremden Zeilen liefern — Voraussetzung ist, dass `SET ROLE` + Kontext zuverlässig gesetzt **und** nach Gebrauch zurückgesetzt werden. Ohne gesetzten Kontext: keine Schüler-Daten.
- **P6 (Mensch im Loop ist Sicherheitsarchitektur):** Der Hook wird in E3 (SAF-1) um `app.current_teacher_id` für Lehrer-Principals erweitert, damit Lehrpersonen ihre Klassen sehen — strukturell hier vorbereitet, inhaltlich Teil von E3.
- **P4 (PII bleibt in der DB):** Übergeben wird nur die `student_id` (UUID), kein Klartext-Profil.

## Zu erstellende/aendernde Dateien

- `apps/api/src/its/db/session.py` — Engine, `SessionLocal`, `scoped_session`.
- (Konsumiert) `apps/api/src/its/config.py` (FND-4): `settings.database_url`.
- (Konsumiert) `apps/api/src/its/auth/roles.py` (FND-5): `Role`, `PG_ROLE`.
- (Konsumiert) `apps/api/src/its/auth/deps.py` (FND-5): `Principal`.

## Schnittstellen & Signaturen

Referenz-Implementierung aus `docs/03-database.md` §5:

```python
from collections.abc import Iterator
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from its.config import settings
from its.auth.deps import Principal
from its.auth.roles import PG_ROLE, Role

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

@contextmanager
def scoped_session(principal: Principal) -> Iterator[Session]:
    """Öffnet eine Session und setzt Rolle + (für Schüler) student_id-Kontext.
    Diese Variablen werden von den RLS-Policies in rls.sql gelesen (docs/04)."""
    session = SessionLocal()
    try:
        pg_role = PG_ROLE[principal.role]
        session.execute(text("SET ROLE :r").bindparams(r=pg_role))
        if principal.role == Role.STUDENT:
            if not principal.student_id:
                raise PermissionError("student principal without student_id (fail-closed)")
            session.execute(
                text("SET app.current_student_id = :sid").bindparams(sid=principal.student_id)
            )
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.execute(text("RESET ROLE"))
        session.close()
```

Kontext aus FND-5 (`auth/roles.py`, `auth/deps.py`) — bereits vorhanden:

```python
class Role(StrEnum):
    STUDENT = "student"; TEACHER = "teacher"; ADMIN = "admin"
PG_ROLE = {Role.STUDENT: "its_student", Role.TEACHER: "its_teacher", Role.ADMIN: "its_admin"}

@dataclass(frozen=True)
class Principal:
    user_id: str
    role: Role
    student_id: str | None = None
```

> Hinweis: zu entscheiden — Postgres parametrisiert `SET ROLE`/`SET app...` über Bind-Params möglicherweise **nicht** wie erwartet (Platzhalter in `SET`-Statements werden nicht serverseitig substituiert). Robuste Alternative für den `student_id`-Kontext: `session.execute(text("SELECT set_config('app.current_student_id', :sid, false)").bindparams(sid=principal.student_id))`. Für `SET ROLE` ggf. den Rollennamen über eine **Allowlist** (`PG_ROLE`-Werte) absichern und nur validierte Bezeichner interpolieren — niemals freien Input. Diese Entscheidung mit SAF-1 (E3) abstimmen.

> Hinweis: zu entscheiden — `app.current_teacher_id` für Lehrer-Principals wird laut `docs/04` ergänzt; ob DB-3 bereits einen no-op-Branch dafür anlegt oder SAF-1 ihn vollständig nachzieht, ist abzustimmen.

## Umsetzungsschritte

- [ ] `engine = create_engine(settings.database_url, pool_pre_ping=True)` und `SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)` anlegen.
- [ ] `scoped_session(principal)` als `@contextmanager` mit Rückgabetyp `Iterator[Session]`.
- [ ] Rolle aus `PG_ROLE[principal.role]` auflösen und `SET ROLE` ausführen (Rollenname gegen Allowlist absichern, siehe Hinweis).
- [ ] Branch `principal.role == Role.STUDENT`: bei fehlender `student_id` → `PermissionError("... fail-closed")`; sonst `app.current_student_id` setzen (bevorzugt via `set_config`).
- [ ] `yield session`; bei Erfolg `commit`, bei Exception `rollback` + re-raise.
- [ ] `finally`: `RESET ROLE` und `session.close()` — die Connection muss rollen-neutral in den Pool zurückkehren (sonst Cross-Request-Leak).
- [ ] TODO/Kommentar für die E3-Erweiterung (`app.current_teacher_id`) hinterlassen, ohne sie zu erfinden.

## Akzeptanzkriterien

- [ ] `scoped_session(principal)` setzt für jede Rolle `SET ROLE` auf den passenden `PG_ROLE`-Wert.
- [ ] Für `Role.STUDENT` wird `app.current_student_id` gesetzt.
- [ ] Ein Schüler-Principal **ohne** `student_id` führt zu `PermissionError` (fail-closed) — es wird keine nutzbare Session geöffnet.
- [ ] Nach Verlassen des Context-Managers ist die Rolle zurückgesetzt (`RESET ROLE`), auch im Fehlerfall.

## Tests / Verifikation

```bash
cd apps/api
# Fail-closed: Schüler ohne student_id -> PermissionError
uv run python -c "
from its.auth.deps import Principal
from its.auth.roles import Role
from its.db.session import scoped_session
try:
    with scoped_session(Principal(user_id='u1', role=Role.STUDENT, student_id=None)) as s:
        pass
    print('FAIL: keine Exception')
except PermissionError as e:
    print('OK fail-closed:', e)
"
# Erwartung: 'OK fail-closed: student principal without student_id (fail-closed)'
```

```bash
# Happy path (setzt voraus, dass die its_student-Rolle existiert; sonst erst nach SAF-1 grün):
uv run python -c "
from sqlalchemy import text
from its.auth.deps import Principal
from its.auth.roles import Role
from its.db.session import scoped_session
import uuid
sid=str(uuid.uuid4())
with scoped_session(Principal(user_id='u1', role=Role.STUDENT, student_id=sid)) as s:
    val=s.execute(text(\"select current_setting('app.current_student_id', true)\")).scalar()
    print('student_id im Kontext:', val)
"
# Erwartung: die gesetzte UUID
```

> Hinweis: Der Happy-Path-Test benötigt die Postgres-Rollen `its_student` etc., die erst in SAF-1 (E3) angelegt werden. Bis dahin ist der **fail-closed**-Test (oben) das verbindliche AK; der Happy-Path-Test ggf. mit `@pytest.mark.skipif`/Marker bis SAF-1 zurückstellen.

## Abhaengigkeiten

- **DB-2** (Voraussetzung): liefert `Base`/Modelle und damit den DB-Kontext, gegen den die Engine arbeitet.
- **FND-4/FND-5** (implizit): `settings.database_url`, `Role`, `PG_ROLE`, `Principal`.
- **Nachgelagert:** **SAF-1** (RLS-Policies lesen `app.current_student_id` und ergänzen `app.current_teacher_id`), **SAF-2** (Scoping-Resolver), **TST-1** (Test-Fixtures für student/teacher-Rollen), **API-1** (alle Student-Endpoints laufen über `scoped_session`).

## Definition of Done

- [ ] Akzeptanzkriterium aus `docs/03` §5/§7 (DB-3: „`scoped_session` setzt Rolle + `app.current_student_id`; fail-closed ohne `student_id`") erfüllt.
- [ ] Fail-closed-Test grün; `RESET ROLE` im `finally` belegt.
- [ ] `uv`-only — keine `pip`-Aufrufe.
- [ ] Keine PII an externe LLMs (nicht betroffen; es wird nur die `student_id`-UUID in den DB-Sessionkontext gesetzt, P4).
- [ ] `safety-critical`: Review erfolgt; die fail-closed-Eigenschaft ist getestet.
- [ ] GitHub-Issue DB-3 geschlossen, E2-Epic-Checkliste aktualisiert.
