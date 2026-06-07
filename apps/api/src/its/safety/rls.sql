-- Row-Level Security: the isolation gate (P1). Run as a versioned Alembic migration
-- (0002_rls_policies). Idempotent where practical so a re-run is harmless.
--
-- Design note (FORCE): we deliberately do NOT enable FORCE ROW LEVEL SECURITY.
-- The login/owner role `its` is the privileged path used by migrations and the
-- mock/production seeders (it bypasses RLS as table owner). Every *user* request
-- instead switches to its_student / its_teacher (db/session.py), where RLS applies.
--
-- fail-closed: current_setting('app.current_*', true) returns NULL when unset;
-- `col = NULL` is never true -> zero rows (never "all rows").

-- ── Roles (idempotent) ────────────────────────────────────────────────────────
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='its_student') THEN CREATE ROLE its_student NOLOGIN; END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='its_teacher') THEN CREATE ROLE its_teacher NOLOGIN; END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='its_admin')   THEN CREATE ROLE its_admin   NOLOGIN; END IF;
END $$;

-- The app login user may switch into these roles (SET ROLE / set_config('role', ...)).
GRANT its_student, its_teacher, its_admin TO its;

-- ── Table grants (RLS narrows further, row by row) ────────────────────────────
GRANT SELECT, INSERT, UPDATE ON attempts, learner_state TO its_student, its_teacher;
GRANT SELECT, INSERT, UPDATE, DELETE ON teacher_notes TO its_teacher;
-- classes added (vs docs/04): the teacher *_in_class policies join classes.
GRANT SELECT ON enrollments, classes, skills, subjects, skill_edges, content_notes, content_embeddings
  TO its_student, its_teacher;

-- ── Enable RLS on person-scoped tables ────────────────────────────────────────
ALTER TABLE attempts        ENABLE ROW LEVEL SECURITY;
ALTER TABLE learner_state   ENABLE ROW LEVEL SECURITY;
ALTER TABLE teacher_notes   ENABLE ROW LEVEL SECURITY;
ALTER TABLE enrollments     ENABLE ROW LEVEL SECURITY;

-- ── STUDENT: only own rows ────────────────────────────────────────────────────
CREATE POLICY student_attempts_self ON attempts
  FOR ALL TO its_student
  USING (student_id = NULLIF(current_setting('app.current_student_id', true), '')::uuid)
  WITH CHECK (student_id = NULLIF(current_setting('app.current_student_id', true), '')::uuid);

CREATE POLICY student_state_self ON learner_state
  FOR ALL TO its_student
  USING (student_id = NULLIF(current_setting('app.current_student_id', true), '')::uuid)
  WITH CHECK (student_id = NULLIF(current_setting('app.current_student_id', true), '')::uuid);

-- Students may READ teacher notes about themselves ("Note from Frau Meier").
CREATE POLICY student_notes_about_self ON teacher_notes
  FOR SELECT TO its_student
  USING (student_id = NULLIF(current_setting('app.current_student_id', true), '')::uuid);

CREATE POLICY student_enrollment_self ON enrollments
  FOR SELECT TO its_student
  USING (student_id = NULLIF(current_setting('app.current_student_id', true), '')::uuid);

-- ── TEACHER: rows of students in their own classes ────────────────────────────
-- Needed so the *_in_class subqueries (which read enrollments under RLS) resolve.
CREATE POLICY teacher_enrollment_in_class ON enrollments
  FOR SELECT TO its_teacher
  USING (class_id IN (
    SELECT id FROM classes
    WHERE teacher_id = NULLIF(current_setting('app.current_teacher_id', true), '')::uuid
  ));

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

-- Teachers read/write only their own notes.
CREATE POLICY teacher_notes_rw ON teacher_notes
  FOR ALL TO its_teacher
  USING (teacher_id = NULLIF(current_setting('app.current_teacher_id', true), '')::uuid)
  WITH CHECK (teacher_id = NULLIF(current_setting('app.current_teacher_id', true), '')::uuid);

-- ADMIN: no blanket BYPASSRLS. Admin functions run through dedicated, audited paths.
