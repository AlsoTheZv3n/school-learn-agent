## Ziel

Die Isolation zwischen Personen wird in der Datenbank verankert: Schueler sehen ausschliesslich eigene Zeilen, Lehrer nur Zeilen der Schueler ihrer Klassen. Rollen, Grants und RLS-Policies werden als **versionierte Alembic-Migration** auf `attempts`, `learner_state`, `teacher_notes`, `enrollments` ausgerollt. Selbst eine fehlerhaft generierte Query darf keine fremden Zeilen liefern (fail-closed).

## Kontext & Prinzipien

- **P1 (Safety zuerst, in der DB verankert):** Der Kern dieses Tasks. Die Isolation wird ueber Postgres Row-Level Security erzwungen, nicht ueber `if`-Checks im App-Code. Selbst eine fehlerhafte Query darf keine fremden Zeilen zurueckgeben. Deshalb wird dieses Paket frueh (M1) gebaut, bevor Features darauf aufsetzen.
- **P8 (Datenresidenz CH/EU):** Es geht um Daten Minderjaehriger; die Zeilenisolation ist die technische Untermauerung der DSG/DSGVO-Pflichten. RLS macht Datenminimierung pro Zugriff erzwingbar.
- **P6 (Mensch im Loop als Sicherheitsarchitektur):** Die Teacher-Policies sind so geschnitten, dass eine Lehrperson genau die Schueler ihrer Klassen sieht (Aufsicht), aber nicht klassenfremde Kinder — Aufsicht ohne Ueberreichweite.

## Zu erstellende/aendernde Dateien

- `apps/api/src/its/safety/rls.sql` — die SQL-Quelle (Rollen, Grants, RLS-Policies). Liegt im `safety/`-Modul gemaess Repo-Layout (Section 6: `safety/ # rls.sql, cohort.py, scoping.py`).
- `apps/api/src/its/db/migrations/versions/0002_rls_policies.py` (Alembic-Migration, die `rls.sql` ausfuehrt). Migrations liegen unter `db/` (Section 6: `db/ # models, session, migrations`).
- `apps/api/src/its/db/session.py` — Ergaenzung von `scoped_session` um `app.current_teacher_id` fuer Lehrer.

## Schnittstellen & Signaturen

`apps/api/src/its/safety/rls.sql` (Referenz aus docs/04 §2 — als idempotente Migration auszufuehren):

```sql
-- Rollen (einmalig; in Migration idempotent via DO-Block)
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='its_student') THEN CREATE ROLE its_student NOLOGIN; END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='its_teacher') THEN CREATE ROLE its_teacher NOLOGIN; END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='its_admin')   THEN CREATE ROLE its_admin   NOLOGIN; END IF;
END $$;

-- Der App-Login-User darf in diese Rollen wechseln (SET ROLE) und liest die Session-Variable.
GRANT its_student, its_teacher, its_admin TO its;

-- Lesezugriff (Tabellen-Grants) — RLS verengt zusaetzlich zeilenweise:
GRANT SELECT, INSERT, UPDATE ON attempts, learner_state TO its_student, its_teacher;
GRANT SELECT, INSERT, UPDATE, DELETE ON teacher_notes TO its_teacher;
GRANT SELECT ON enrollments, skills, subjects, skill_edges, content_notes, content_embeddings
  TO its_student, its_teacher;

-- RLS auf personenbezogenen Tabellen aktivieren
ALTER TABLE attempts        ENABLE ROW LEVEL SECURITY;
ALTER TABLE learner_state   ENABLE ROW LEVEL SECURITY;
ALTER TABLE teacher_notes   ENABLE ROW LEVEL SECURITY;
ALTER TABLE enrollments     ENABLE ROW LEVEL SECURITY;

-- STUDENT: sieht ausschliesslich eigene Zeilen
CREATE POLICY student_attempts_self ON attempts
  FOR ALL TO its_student
  USING (student_id = NULLIF(current_setting('app.current_student_id', true), '')::uuid)
  WITH CHECK (student_id = NULLIF(current_setting('app.current_student_id', true), '')::uuid);

CREATE POLICY student_state_self ON learner_state
  FOR ALL TO its_student
  USING (student_id = NULLIF(current_setting('app.current_student_id', true), '')::uuid)
  WITH CHECK (student_id = NULLIF(current_setting('app.current_student_id', true), '')::uuid);

-- Schueler duerfen Lehrernotizen ueber sich LESEN
CREATE POLICY student_notes_about_self ON teacher_notes
  FOR SELECT TO its_student
  USING (student_id = NULLIF(current_setting('app.current_student_id', true), '')::uuid);

CREATE POLICY student_enrollment_self ON enrollments
  FOR SELECT TO its_student
  USING (student_id = NULLIF(current_setting('app.current_student_id', true), '')::uuid);

-- TEACHER: sieht Zeilen der Schueler:innen in seinen/ihren Klassen
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

-- ADMIN: BYPASSRLS bewusst NICHT pauschal. Admin-Funktionen laufen ueber dedizierte,
-- gepruefte Pfade.
```

`scoped_session` (DB-3, `db/session.py`) — Ist-Zustand laut docs/03 §5; **zu ergaenzen** ist der Teacher-Zweig:

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
            session.execute(
                text("SET app.current_student_id = :sid").bindparams(sid=principal.student_id)
            )
        # ── ERGAENZEN (SAF-1): Lehrer-Kontext fuer teacher_*_in_class-Policies ──
        # if principal.role == Role.TEACHER:
        #     session.execute(
        #         text("SET app.current_teacher_id = :tid").bindparams(tid=principal.user_id)
        #     )
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.execute(text("RESET ROLE"))
        session.close()
```

**Warum `current_setting(..., true)` + `NULLIF`:** Ist die Variable nicht gesetzt, ergibt der Ausdruck `NULL`; `student_id = NULL` ist niemals wahr → fail-closed (keine Zeilen statt aller Zeilen).

## Umsetzungsschritte

- [ ] `apps/api/src/its/safety/rls.sql` mit dem obigen Inhalt anlegen (Rollen-DO-Block, Grants, `ENABLE ROW LEVEL SECURITY`, Student-/Teacher-Policies, Admin-Hinweis).
- [ ] Pruefen, dass die Teacher-Policy-Subquery `classes` lesen darf — `GRANT SELECT ON classes TO its_teacher` ergaenzen (in docs/04 §2 nicht explizit aufgefuehrt).
- [ ] Alembic-Migration `0002_rls_policies` erstellen; in `upgrade()` den Inhalt von `rls.sql` lesen und via `op.execute(<sql>)` ausfuehren.
- [ ] `downgrade()` schreiben: `DROP POLICY IF EXISTS ...` je Policy + `ALTER TABLE ... DISABLE ROW LEVEL SECURITY`; Rollen-Drop optional (i. d. R. nicht droppen, da geteilt).
- [ ] `db/session.py`: den auskommentierten Teacher-Zweig aktivieren — fuer `Role.TEACHER` `SET app.current_teacher_id = :tid` mit `principal.user_id`.
- [ ] Entscheiden und ggf. umsetzen: `ALTER TABLE ... FORCE ROW LEVEL SECURITY`, falls der App-Login `its` zugleich Tabellen-Owner ist (sonst greift RLS fuer ihn nicht).
- [ ] Lokal verifizieren: `uv run alembic upgrade head` gegen die Docker-DB; `psql ... -c "\\d+ attempts"` zeigt "Row security: enabled".
- [ ] Manueller Gegencheck: als `its_student` mit gesetzter `app.current_student_id` nur eigene `attempts` sichtbar; ohne gesetzte Variable 0 Zeilen.

> Hinweis: zu entscheiden — `FORCE ROW LEVEL SECURITY` ja/nein. docs/04 spezifiziert nur `ENABLE`; ob der App-User Owner ist, geht aus den Docs nicht eindeutig hervor. Empfehlung: `FORCE` setzen, um Owner-Bypass auszuschliessen.
> Hinweis: zu entscheiden — Migrationsname/-nummer (`0002_rls_policies` als Vorschlag) und sync-vs-async-`env.py` (docs/03 nennt beide). Empfehlung fuer M1: sync.

## Akzeptanzkriterien

- [ ] `rls.sql` existiert und wird als Alembic-Migration ausgefuehrt (nicht haendisch).
- [ ] RLS ist auf `attempts`, `learner_state`, `teacher_notes`, `enrollments` aktiviert.
- [ ] Rollen `its_student`, `its_teacher`, `its_admin` existieren (idempotent via DO-Block); `its` darf in sie wechseln.
- [ ] Schueler-Policy ist fail-closed: ohne gesetzte `app.current_student_id` werden 0 Zeilen geliefert (via `current_setting(..., true)` + `NULLIF`).
- [ ] Lehrer sehen via `teacher_*_in_class` nur Zeilen der Schueler ihrer Klassen.
- [ ] `scoped_session` setzt zusaetzlich `app.current_teacher_id` fuer Lehrer.
- [ ] Admin erhaelt **kein** pauschales `BYPASSRLS`.

## Tests / Verifikation

```bash
# DB hochfahren
docker compose -f infra/docker-compose.yml up -d

# Migration inkl. RLS anwenden (uv-only, P9)
cd apps/api && uv run alembic upgrade head

# RLS-Status pruefen — erwartet: "Row security: enabled" je Tabelle
psql "postgresql://its:its_dev_pw@localhost:5432/its" -c "\\d+ attempts"

# Smoke: als Schueler-Rolle ohne gesetzte Variable -> 0 Zeilen (fail-closed)
psql "postgresql://its:its_dev_pw@localhost:5432/its" \
  -c "SET ROLE its_student; SELECT count(*) FROM attempts; RESET ROLE;"
```

Erwartete Ergebnisse: `\d+ attempts` listet "Row security: enabled" und die Policies `student_attempts_self`, `teacher_attempts_in_class`; die Smoke-Query liefert `0`. Die formale Pruefung erfolgt CI-seitig durch `tests/test_rls.py` (SAF-4).

## Abhaengigkeiten

- **DB-3** — liefert `scoped_session` und das Schema (`attempts`, `learner_state`, `teacher_notes`, `enrollments`, `classes`, `enrollments`), auf das die Policies aufsetzen; ohne die Tabellen schlaegt `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` fehl.
- Nachgelagert warten: **SAF-2** (anwendungsseitige Schranke ergaenzt diese DB-Schranke), **SAF-4** (beweist diese Policies), **RET-3** (individual-Query, doppelt durch RLS gesichert), **API-2** (Teacher-Endpunkte verlassen sich auf `teacher_*_in_class`), **TST-1** (`DBFactory` spiegelt die Rollen-Variablen).

## Definition of Done

- [ ] Akzeptanzkriterien aus docs/04 §6 (RLS-Teil) erfuellt.
- [ ] Tests gruen, inkl. der Safety-Tests `tests/test_rls.py` (sobald SAF-4 vorliegt).
- [ ] Kein PII-Bezug in externen LLM-Prompts (hier nicht betroffen; reine DB-Schicht).
- [ ] `uv`-only — Migration via `uv run alembic ...`, keine `pip`-Aufrufe.
- [ ] Zugehoeriges GitHub-Issue SAF-1 geschlossen, E3-Epic-Checkliste aktualisiert.
