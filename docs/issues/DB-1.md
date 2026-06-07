## Ziel

Eine Alembic-Migration `0001_core_schema` erzeugt das **gesamte Kern-Schema** des ITS in einer laufenden Postgres-16-DB (mit `pgvector`): alle 12 Tabellen, alle Fremdschlüssel/zusammengesetzten Primärschlüssel und alle Indizes — **inklusive des HNSW-Index** auf der Embedding-Spalte. Nach `uv run alembic upgrade head` ist das Schema vollständig und reproduzierbar; `downgrade` rollt es sauber zurück.

## Kontext & Prinzipien

- **P1 (Safety zuerst, in der DB verankert):** Das Schema wird früh (Milestone M1) gebaut, bevor Features aufsetzen. RLS (E3) ist Schema und muss mit dem Schema migrieren — deshalb gehören Tabellen zwingend in versionierte Alembic-Migrationen, nicht in `infra/init`. `infra/init` aktiviert ausschliesslich die Extensions (`vector`, `uuid-ossp`).
- **P4 (PII-Minimierung):** `students` enthält nur `display_name`, `grade_level`, `created_at` — kein Freitext-Profil. Identifizierendes bleibt in der DB.
- **P5 (Open Learner Model):** `learner_state` trägt neben `mastery` eine `uncertainty`-Spalte, damit der Lernstand später interpretierbar dargestellt werden kann.
- **P8 (Residenz/Löschung):** `ON DELETE CASCADE` auf personenbezogenen Tabellen bereitet den Löschpfad pro Schüler:in (Recht auf Löschung) vor.

## Zu erstellende/aendernde Dateien

- `apps/api/alembic.ini` — Alembic-Konfiguration (sofern noch nicht aus FND-2 vorhanden).
- `apps/api/migrations/env.py` — liest `settings.database_url` und `Base.metadata`.
- `apps/api/migrations/versions/0001_core_schema.py` — die Migration selbst.
- (Konsumiert) `infra/init/01-extensions.sql` — nur Extensions, **keine** Tabellen (bereits aus FND-3).

> Hinweis: zu entscheiden — Alembic **sync vs. async** (`uv run alembic init -t async ...` vs. sync). Empfehlung sync für M1; den genauen Verzeichnisnamen (`migrations/` vs. `alembic/`) konsistent in `alembic.ini` (`script_location`) festhalten.

## Schnittstellen & Signaturen

Referenz-DDL (aus `docs/03-database.md` §3) — die Migration muss exakt diese Strukturen erzeugen:

```sql
CREATE TABLE students (
  id           uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  display_name text NOT NULL,
  grade_level  int  NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE teachers (
  id           uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  display_name text NOT NULL
);
CREATE TABLE classes (
  id          uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  name        text NOT NULL,
  teacher_id  uuid REFERENCES teachers(id)
);
CREATE TABLE enrollments (
  student_id uuid REFERENCES students(id) ON DELETE CASCADE,
  class_id   uuid REFERENCES classes(id)  ON DELETE CASCADE,
  PRIMARY KEY (student_id, class_id)
);
CREATE TABLE subjects (
  id   uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  key  text UNIQUE NOT NULL,               -- 'math' | 'language' | 'history'
  name text NOT NULL
);
CREATE TABLE skills (
  id          uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  subject_id  uuid REFERENCES subjects(id),
  key         text NOT NULL,
  name        text NOT NULL,
  grade_level int  NOT NULL,
  UNIQUE (subject_id, key)
);
CREATE TABLE skill_edges (
  from_skill uuid REFERENCES skills(id) ON DELETE CASCADE,
  to_skill   uuid REFERENCES skills(id) ON DELETE CASCADE,
  kind       text NOT NULL DEFAULT 'prerequisite',  -- prerequisite | related
  PRIMARY KEY (from_skill, to_skill, kind)
);
CREATE TABLE content_notes (
  id         uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  skill_id   uuid REFERENCES skills(id),
  source_path text NOT NULL,
  prose      text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE content_embeddings (
  id         uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  note_id    uuid REFERENCES content_notes(id) ON DELETE CASCADE,
  chunk      text NOT NULL,
  embedding  vector(1024) NOT NULL,        -- Dim an Modell anpassen
  sidecar_query text
);
CREATE INDEX ON content_embeddings USING hnsw (embedding vector_cosine_ops);
CREATE TABLE attempts (
  id          uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  student_id  uuid NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  skill_id    uuid NOT NULL REFERENCES skills(id),
  item_ref    text NOT NULL,
  is_correct  boolean NOT NULL,
  raw_answer  text,
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON attempts (student_id, skill_id, created_at);
CREATE TABLE learner_state (
  student_id  uuid NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  skill_id    uuid NOT NULL REFERENCES skills(id),
  mastery     double precision NOT NULL DEFAULT 0.0,
  uncertainty double precision NOT NULL DEFAULT 1.0,
  attempts_count int NOT NULL DEFAULT 0,
  updated_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (student_id, skill_id)
);
CREATE TABLE teacher_notes (
  id          uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  student_id  uuid NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  teacher_id  uuid NOT NULL REFERENCES teachers(id),
  skill_id    uuid REFERENCES skills(id),
  body        text NOT NULL,
  override_mastery double precision,
  created_at  timestamptz NOT NULL DEFAULT now()
);
```

Extensions (aus `infra/init/01-extensions.sql`, FND-3 — Voraussetzung, nicht Teil dieser Migration):

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

Migrationsskizze (HNSW per `op.execute`, da Alembic die Opclass nicht nativ kennt):

```python
# 0001_core_schema.py (Auszug)
import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

def upgrade() -> None:
    op.create_table("students", ... )
    # ... alle weiteren Tabellen ...
    op.create_index("ix_attempts_student_skill_time", "attempts",
                    ["student_id", "skill_id", "created_at"])
    op.execute(
        "CREATE INDEX ix_content_embeddings_hnsw ON content_embeddings "
        "USING hnsw (embedding vector_cosine_ops)"
    )

def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_content_embeddings_hnsw")
    # Drop in FK-sicherer Reihenfolge ...
```

## Umsetzungsschritte

- [ ] Alembic in `apps/api` initialisieren (sync/async-Entscheidung treffen); `script_location` in `alembic.ini` setzen.
- [ ] `migrations/env.py`: `settings.database_url` aus `its.config` einlesen; `target_metadata = Base.metadata` (Import aus `its.db.models`); `compare_type=True` setzen.
- [ ] Sicherstellen, dass `from pgvector.sqlalchemy import Vector` in der Migrations-Umgebung importierbar ist (sonst wird `vector(1024)` nicht korrekt emittiert).
- [ ] Migration `0001_core_schema` als `down_revision = None` (erste Revision) anlegen.
- [ ] Alle 12 Tabellen exakt gemäss DDL erstellen: `students`, `teachers`, `classes`, `enrollments`, `subjects`, `skills`, `skill_edges`, `content_notes`, `content_embeddings`, `attempts`, `learner_state`, `teacher_notes`.
- [ ] Zusammengesetzte Primärschlüssel: `enrollments(student_id, class_id)`, `skill_edges(from_skill, to_skill, kind)`, `learner_state(student_id, skill_id)`.
- [ ] Unique-Constraints: `subjects.key`, `skills(subject_id, key)`.
- [ ] `ON DELETE CASCADE` setzen wo in der DDL angegeben (enrollments, content_embeddings, attempts, learner_state, teacher_notes, skill_edges).
- [ ] `DEFAULT uuid_generate_v4()` und `DEFAULT now()` auf den entsprechenden Spalten.
- [ ] Sekundärindex `attempts(student_id, skill_id, created_at)`.
- [ ] HNSW-Index per `op.execute("... USING hnsw (embedding vector_cosine_ops)")`.
- [ ] `downgrade()` vollständig (alle Indizes + Tabellen in FK-sicherer Reihenfolge droppen).
- [ ] Migration gegen die Docker-DB ausführen und reversibel prüfen (`upgrade head` → `downgrade base` → `upgrade head`).

## Akzeptanzkriterien

- [ ] Migration `0001_core_schema` erstellt **alle 12 Tabellen** (`students`, `teachers`, `classes`, `enrollments`, `subjects`, `skills`, `skill_edges`, `content_notes`, `content_embeddings`, `attempts`, `learner_state`, `teacher_notes`).
- [ ] Der **HNSW-Index** auf `content_embeddings(embedding)` mit `vector_cosine_ops` existiert nach `upgrade`.
- [ ] Der Sekundärindex auf `attempts(student_id, skill_id, created_at)` existiert.
- [ ] Zusammengesetzte PKs und Unique-Constraints entsprechen der DDL.
- [ ] `uv run alembic upgrade head` läuft fehlerfrei gegen die Docker-DB; `downgrade base` rollt vollständig zurück.
- [ ] `infra/init` enthält **keine** Tabellen-DDL (nur Extensions).

## Tests / Verifikation

```bash
# Voraussetzung: DB läuft (FND-3)
docker compose -f infra/docker-compose.yml up -d

cd apps/api
uv run alembic upgrade head
# Erwartung: endet mit "Running upgrade  -> 0001_core_schema"

# Smoke: alle Tabellen vorhanden (12 erwartet)
uv run python -c "from sqlalchemy import create_engine, text; from its.config import settings; \
e=create_engine(settings.database_url); \
print(sorted(r[0] for r in e.connect().execute(text(\"select table_name from information_schema.tables where table_schema='public'\"))))"

# Smoke: HNSW-Index vorhanden
uv run python -c "from sqlalchemy import create_engine, text; from its.config import settings; \
e=create_engine(settings.database_url); \
print([r[0] for r in e.connect().execute(text(\"select indexname from pg_indexes where tablename='content_embeddings'\"))])"
# Erwartung: ein Index mit hnsw in der Definition

uv run alembic downgrade base   # muss fehlerfrei zurückrollen
uv run alembic upgrade head
```

## Abhaengigkeiten

- **FND-3** (Voraussetzung): liefert die laufende Postgres-16-Instanz mit aktivierten Extensions `vector`/`uuid-ossp` — ohne sie schlägt `vector(1024)` und `uuid_generate_v4()` fehl.
- **FND-2** (implizit): liefert das `uv`-Projekt mit Alembic/SQLAlchemy/psycopg als Dependencies.
- **Nachgelagert:** **DB-2** (Modelle bauen auf demselben Schema auf), **DB-4** (Seed setzt die Tabellen voraus), **SAF-1** (RLS-Migration setzt das Schema voraus), **alle Retrieval-/Learner-/Seeder-Tasks**.

## Definition of Done

- [ ] Akzeptanzkriterien aus `docs/03` §7 (DB-1: „Migration `0001_core_schema` erstellt alle Tabellen + HNSW-Index") erfüllt.
- [ ] `upgrade head`/`downgrade base` grün gegen die Docker-DB; Smoke-Skript bestätigt Tabellen + HNSW-Index.
- [ ] `uv`-only — keine `pip`-Aufrufe (Migration via `uv run alembic ...`).
- [ ] Keine PII in externen LLM-Prompts (für diesen Task nicht betroffen, aber Schema hält PII minimal, P4).
- [ ] GitHub-Issue DB-1 geschlossen, E2-Epic-Checkliste aktualisiert.
