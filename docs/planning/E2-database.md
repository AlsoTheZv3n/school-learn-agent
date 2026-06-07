# E2 — Database: Schema & Migrationen — Detailplanung

> Milestone: **M1 — Data Layer & Safety**. Quelldokument: `docs/03-database.md` (im Verbund mit `docs/00-architecture.md`, `docs/02-foundations.md`, `docs/04-safety.md`, `docs/11-mock-data-and-production.md`).

## 1. Scope & Zielbild

E2 baut das **datenmodellige Fundament** des ITS: ein einziges PostgreSQL-Schema (mit `pgvector`), das alle drei Retrieval-Modi (semantic / individual / population) aus *einer* Datenbank bedient, plus den Session-/Engine-Hook, der später (E3) die Row-Level-Security speist.

Konkret entsteht:
- eine Alembic-Migration `0001_core_schema`, die alle 12 Tabellen + Indizes (inkl. HNSW auf der Embedding-Spalte) erzeugt (DB-1);
- vollständige, typisierte SQLAlchemy-2.0-Modelle für jede Tabelle inkl. `pgvector`-Spalte (DB-2);
- `db/session.py` mit `scoped_session(principal)`, das pro Request die Postgres-Rolle setzt und für Schüler:innen `app.current_student_id` als Session-Variable hinterlegt — **fail-closed** (DB-3);
- ein kleiner, idempotenter Mathematik-Skill-Graph-Seed (Fach `math`, ~3 Skills + `skill_edges`) als Daten-Migration (DB-4).

Was E2 **nicht** umfasst (bewusst abgegrenzt): RLS-Policies/Rollen-Definition selbst (E3/SAF-1 — liest aber den Hook aus DB-3), Min-Cohort-Logik (E3/SAF-3), Embeddings tatsächlich befüllen (E5/CON-2), der realistische Mock-Seeder mit Lernkurven (E13/MOCK-1..3). E2 legt nur die Strukturen und den schmalen Seed an.

Zielbild am Ende von E2: `uv run alembic upgrade head` gegen die Docker-DB erzeugt das gesamte Schema; ein Smoke-Skript bestätigt, dass alle Tabellen, der HNSW-Index und der Demo-Skill-Graph existieren; `scoped_session` lässt sich für ein Schüler-Principal öffnen und wirft bei fehlender `student_id` einen `PermissionError`.

## 2. Task-Reihenfolge & Abhängigkeiten

```
FND-3 (Postgres+pgvector, infra)  ─┐
FND-2 (uv/Alembic, deps)          ─┤
                                   ▼
                                 DB-1 (0001_core_schema: alle Tabellen + HNSW)
                                 ├──────────────► DB-2 (SQLAlchemy-Modelle)
                                 │                      ▼
                                 │                DB-3 (scoped_session, Rollen-/student_id-Hook)
                                 │                      ▼
                                 │                [E3] SAF-1 (RLS) ── erweitert DB-3 um teacher_id
                                 └──────────────► DB-4 (Math-Skill-Graph-Seed)

Nachgelagert (warten auf E2):
  DB-2 → RET-2/3/5 (Retrieval), LM-2 (Tracing), MOCK-1 (Seeder), CON-2 (Ingestion)
  DB-3 → SAF-1/SAF-2 (Safety, RLS-Brücke), TST-1 (Test-Fixtures)
```

Kompakt:
- **DB-1** zuerst (hängt an FND-2 für Alembic und FND-3 für die laufende DB + Extensions).
- **DB-2** und **DB-4** hängen beide nur an DB-1 und sind danach parallelisierbar. Empfehlung: DB-2 vor DB-4, weil der Seed bequemer über die ORM-Modelle geschrieben wird (statt rohem SQL).
- **DB-3** hängt an DB-2 (braucht `SessionLocal`/Engine) und ist der kritische Übergabepunkt an E3.

## 3. Feinere Sub-Task-Zerlegung (über die Issues hinaus)

**DB-1 — Kern-Schema-Migration**
1. Alembic in `apps/api` initialisieren; Entscheidung sync vs. async treffen (siehe §4) und im `env.py` festhalten.
2. `env.py`: `settings.database_url` und `Base.metadata` (aus `db.models`) verdrahten; `compare_type=True` für saubere Autogeneration aktivieren.
3. `pgvector`-Typ in Alembic verfügbar machen (Import `from pgvector.sqlalchemy import Vector`), damit `vector(1024)` korrekt emittiert wird.
4. Migration `0001_core_schema` schreiben — bevorzugt **explizit von Hand** (nicht blind autogeneriert), damit HNSW-Index, `uuid_generate_v4()`-Defaults und zusammengesetzte PKs exakt der DDL aus docs/03 entsprechen.
5. HNSW-Index `USING hnsw (embedding vector_cosine_ops)` per `op.execute(...)` ergänzen (Alembic kennt HNSW-Opclass nicht nativ).
6. Sekundärindizes: `attempts (student_id, skill_id, created_at)`.
7. `downgrade()` vollständig implementieren (Drop in FK-sicherer Reihenfolge).
8. Migration gegen Docker-DB hoch- und wieder runterfahren (`upgrade head` / `downgrade base`) zur Reversibilitätsprüfung.

**DB-2 — SQLAlchemy-Modelle**
1. `Base(DeclarativeBase)` definieren.
2. Alle 12 Modelle nach dem Doc-Muster: `Student`, `Teacher`, `Class`, `Enrollment`, `Subject`, `Skill`, `SkillEdge`, `ContentNote`, `ContentEmbedding`, `Attempt`, `LearnerState`, `TeacherNote`.
3. Zusammengesetzte Primärschlüssel für `enrollments` (student_id+class_id), `learner_state` (student_id+skill_id), `skill_edges` (from_skill+to_skill+kind).
4. `UniqueConstraint` für `subjects.key` und `(subject_id, key)` auf `skills`.
5. `Vector(1024)`-Spalte (Dimension als benannte Konstante, siehe offene Frage).
6. `relationship()`-Definitionen nur dort, wo später gebraucht (z. B. `Skill.subject`, `ContentEmbedding.note`) — sparsam, ohne über das Schema hinaus zu erfinden.
7. Konsistenzcheck: `Base.metadata` muss exakt das erzeugen, was DB-1 migriert (gegenseitige Validierung via Autogenerate-Diff = leer).

**DB-3 — Session-/Engine-Setup mit Rollen-Hook**
1. `engine = create_engine(settings.database_url, pool_pre_ping=True)`; `SessionLocal = sessionmaker(...)`.
2. `scoped_session(principal)` als `@contextmanager` exakt nach Doc-Auszug.
3. Fail-closed-Branch: Schüler-Principal ohne `student_id` → `PermissionError`.
4. `RESET ROLE` im `finally` sicherstellen (Connection kehrt sauber in den Pool zurück).
5. Vorbereitende Naht für E3: Kommentar/TODO, dass SAF-1 hier `SET app.current_teacher_id` für TEACHER ergänzt (nicht selbst erfinden — gehört zu E3).
6. Sicherstellen, dass `SET ROLE`/`SET` pro Session laufen (nicht pro Connection-Pool-übergreifend hängen bleiben).

**DB-4 — Math-Skill-Graph-Seed**
1. Daten-Migration `0002_seed_math_skills` (oder separates idempotentes Seed-Skript — Entscheidung siehe §6).
2. Fach `math` anlegen (idempotent: `INSERT ... ON CONFLICT (key) DO NOTHING` bzw. Existenz-Check).
3. Skills: `linear-equations`, `complete-the-square`, `quadratic-formula` (grade_level z. B. 8/9) idempotent.
4. Kanten: `linear-equations → complete-the-square → quadratic-formula` mit `kind='prerequisite'`.
5. `downgrade()` entfernt genau diese Seed-Zeilen.

## 4. Zentrale Designentscheidungen (mit Begründung)

- **Tabellen ausschliesslich über Alembic, `infra/init` nur für Extensions.** docs/03 §3 ist explizit: `infra/init/01-extensions.sql` aktiviert `vector` und `uuid-ossp`; alle Tabellen kommen aus DB-1. Begründung: versioniertes, reproduzierbares Schema; RLS (E3) muss als Migration mitwandern.
- **HNSW + `vector_cosine_ops` von Anfang an.** Der Semantic-Modus nutzt Kosinus-Ähnlichkeit; der Index gehört ins Kern-Schema, damit RET-2 ohne Schemaänderung darauf bauen kann.
- **Hook in der DB-Schicht, nicht im App-Code (P1).** `scoped_session` setzt `SET ROLE` + `SET app.current_student_id`; die eigentliche Filterung macht später RLS (E3). E2 liefert die *Brücke*, nicht die Policy — saubere Schichtentrennung.
- **Fail-closed als Default (P1).** Fehlt `student_id`, wird gar keine Session geöffnet (`PermissionError`), statt eine unscoped Session zu riskieren. Das ist die App-seitige Hälfte des fail-closed; die DB-seitige Hälfte (`current_setting(..., true)` → NULL → keine Zeilen) folgt in E3.
- **PII-Minimierung im Schema (P4).** `students` hält nur `display_name`, `grade_level`, `created_at` — kein Freitext-Profil. Identifizierendes bleibt in der DB; der LLM-Pfad bekommt nur Skill-IDs/anonymisierten Kontext (relevant erst ab E8, aber das Schema setzt die Leitplanke jetzt).
- **`ON DELETE CASCADE` auf personenbezogenen Tabellen** (`enrollments`, `attempts`, `learner_state`, `teacher_notes` → `students`): bereitet den Löschpfad für einzelne Schüler:innen vor (PROD-3 Retention/Recht-auf-Löschung, P8).
- **Seed klein halten (DB-4).** Nur ein lauffähiger Demo-Graph; echte Mengen kommen über den Seeder (docs/11). Vermeidet Vermischung von Stammdaten-Seed und Mock-Personendaten.

## 5. Risiken & Gegenmassnahmen

| Risiko | Gegenmassnahme |
|---|---|
| HNSW-Index/`vector`-Opclass wird von Alembic-Autogenerate nicht erkannt → fehlt nach Migration | Index explizit per `op.execute("CREATE INDEX ... USING hnsw ...")` in der Migration; im Smoke-Test gegen `pg_indexes` prüfen. |
| `vector(1024)` ist Platzhalter; tatsächliche Embedding-Dimension hängt am noch ungewählten Modell | Dimension als benannte Konstante (`EMBEDDING_DIM`) zentralisieren; offene Frage explizit markieren; spätere Änderung = eigene Migration. |
| `scoped_session` ohne `RESET ROLE` → Connection kehrt mit fremder Rolle in den Pool zurück (Cross-Request-Leak) | `RESET ROLE` zwingend im `finally`; in E3-Tests (test_rls) gegengeprüft. |
| `SET ROLE`/`SET app.current_student_id` ist ohne die in E3 angelegten Rollen (`its_student` …) wirkungslos oder schlägt fehl | DB-3 ist *Vorbereitung*; Hook tolerant gegen noch fehlende Policies, aber Rollen-Namen via `PG_ROLE` (FND-5); Reihenfolge DB-3 → SAF-1 strikt einhalten. |
| Modelle (DB-2) und Migration (DB-1) driften auseinander | Autogenerate-Diff muss leer sein (`alembic revision --autogenerate` zeigt keine Änderungen) — als Verifikationsschritt. |
| `psycopg`-Bind-Parameter in `SET ROLE :r` / `SET app.current_student_id = :sid` werden nicht wie erwartet quotiert (Postgres erlaubt bei `SET ROLE` keinen Parameter-Platzhalter) | Hinweis im Body markiert: ggf. `SET LOCAL` + `set_config('app.current_student_id', :sid, false)` statt String-Interpolation; sicher gegen Injection halten. |

## 6. Offene Fragen / zu treffende Entscheidungen

1. **Alembic sync vs. async.** docs/03 §6 lässt offen (`-t async ... bzw. sync`). Empfehlung: **sync** für M1 (psycopg3 sync, einfacher zu testen; RLS-Tests laufen synchron). Async später nur bei gemessenem Bedarf.
2. **Embedding-Dimension `1024`.** Platzhalter im Schema; das konkrete Embedding-Modell ist nicht festgelegt. Muss vor CON-2/RET-2 entschieden werden, sonst Index/Spalte falsch dimensioniert.
3. **DB-4 als Daten-Migration vs. separates Seed-Skript.** docs/03 §6 spricht von „Daten-Migration/Seed". Stammdaten (Fächer/Skills) gehören eher in eine versionierte Migration; Personendaten in den Seeder (docs/11). Empfehlung: Stammdaten-Seed als Migration `0002_seed_math_skills`.
4. **`set_config` vs. `SET app.current_student_id = :sid`.** Postgres parametrisiert `SET ...` nicht; sichere Übergabe der UUID muss geklärt werden (s. Risiko oben).
5. **`teacher_id`-Hook-Naht.** docs/04 verlangt, dass `scoped_session` für Lehrer `app.current_teacher_id` setzt — gehört formal zu SAF-1. Klären, ob DB-3 die Naht bereits als no-op-Branch anlegt oder E3 sie vollständig nachzieht.

## 7. Test-/Verifikationsstrategie für das Epic

- **Voraussetzung:** `docker compose -f infra/docker-compose.yml up -d` (FND-3) — DB läuft, `vector` + `uuid-ossp` aktiviert.
- **DB-1:** `cd apps/api && uv run alembic upgrade head`; danach Smoke gegen `information_schema.tables` (alle 12 Tabellen vorhanden) und `pg_indexes` (HNSW-Index auf `content_embeddings`); `uv run alembic downgrade base` muss fehlerfrei zurückrollen.
- **DB-2:** `uv run alembic revision --autogenerate -m check` darf **keine** Schemaänderung erzeugen (Modelle == Migration). Roundtrip-Smoke: ein `Student` + `Attempt` per ORM einfügen und zurücklesen; eine `ContentEmbedding` mit `Vector`-Wert schreiben/lesen.
- **DB-3:** Unit-Test (ohne RLS-Rollen ggf. gemockt/markiert): `scoped_session` mit Schüler-Principal **ohne** `student_id` wirft `PermissionError`; mit `student_id` öffnet die Session und führt `SET app.current_student_id` aus.
- **DB-4:** Query bestätigt Fach `math`, 3 Skills und die 2 Prerequisite-Kanten; rekursive CTE über `skill_edges` liefert den Pfad `linear-equations → complete-the-square → quadratic-formula`.
- **Epic-Gate:** Diese Verifikationen laufen lokal grün und in CI (FND-6, Postgres-Service) gegen `uv run pytest -q`. E3-Safety-Tests (test_rls) sind **nicht** Teil von E2, setzen aber DB-1/DB-3 voraus.
