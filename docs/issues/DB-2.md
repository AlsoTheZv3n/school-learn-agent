## Ziel

Vollständige, typisierte **SQLAlchemy-2.0-Modelle** für alle 12 Tabellen des Kern-Schemas in `db/models.py`, inkl. funktionierender `pgvector`-Spalte für Embeddings. `Base.metadata` entspricht exakt der Migration aus DB-1 (Autogenerate-Diff ist leer).

## Kontext & Prinzipien

- **P1 (Safety in der DB):** Die Modelle spiegeln das migrierte Schema 1:1; die App definiert keine abweichenden Strukturen, die RLS umgehen könnten. `learner_state`/`attempts`/`teacher_notes` werden später RLS-geschützt — die Modelle dürfen keine impliziten Lade-Pfade quer zur Isolation erfinden.
- **P4 (PII-Minimierung):** Das `Student`-Modell trägt nur `display_name`, `grade_level`, `created_at` — kein Zusatzfeld erfinden.
- **P5 (Open Learner Model):** `LearnerState` modelliert `mastery` **und** `uncertainty` als separate, inspizierbare Felder.
- **P3 (Learner-Modell verbessert sich):** `learner_state` ist die inspizierbare Mastery-Schätzung pro (student, skill) — die Modelle machen genau dieses Feld zur ersten Klasse.

## Zu erstellende/aendernde Dateien

- `apps/api/src/its/db/models.py` — alle Modelle + `Base`.
- (Optional) `apps/api/src/its/db/__init__.py` — Re-Export von `Base` für `env.py` (DB-1).

## Schnittstellen & Signaturen

Muster aus `docs/03-database.md` §4 (Auszug — gilt für alle Tabellen analog):

```python
import uuid
from datetime import datetime
from sqlalchemy import ForeignKey, String, Boolean, Integer, Float, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

class Base(DeclarativeBase):
    pass

class Student(Base):
    __tablename__ = "students"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    grade_level: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Attempt(Base):
    __tablename__ = "attempts"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    skill_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("skills.id"))
    item_ref: Mapped[str] = mapped_column(String, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    raw_answer: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class LearnerState(Base):
    __tablename__ = "learner_state"
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), primary_key=True)
    skill_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("skills.id"), primary_key=True)
    mastery: Mapped[float] = mapped_column(Float, default=0.0)
    uncertainty: Mapped[float] = mapped_column(Float, default=1.0)
    attempts_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class ContentEmbedding(Base):
    __tablename__ = "content_embeddings"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    note_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("content_notes.id", ondelete="CASCADE"))
    chunk: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1024), nullable=False)
    sidecar_query: Mapped[str | None] = mapped_column(Text)
```

> Restliche Modelle (`Teacher`, `Class`, `Enrollment`, `Subject`, `Skill`, `SkillEdge`, `ContentNote`, `TeacherNote`) nach demselben Muster (vgl. DDL in DB-1).

Zusammengesetzte Schlüssel/Constraints, die in den Modellen abzubilden sind:

```python
from sqlalchemy import UniqueConstraint

class Enrollment(Base):
    __tablename__ = "enrollments"
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), primary_key=True)
    class_id:   Mapped[uuid.UUID] = mapped_column(ForeignKey("classes.id",  ondelete="CASCADE"), primary_key=True)

class SkillEdge(Base):
    __tablename__ = "skill_edges"
    from_skill: Mapped[uuid.UUID] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True)
    to_skill:   Mapped[uuid.UUID] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True)
    kind:       Mapped[str] = mapped_column(Text, primary_key=True, default="prerequisite")

class Skill(Base):
    __tablename__ = "skills"
    # ... id, subject_id, key, name, grade_level ...
    __table_args__ = (UniqueConstraint("subject_id", "key"),)
```

> Hinweis: zu entscheiden — die Embedding-Dimension `1024` ist im Doc als Platzhalter markiert ("Dim an Modell anpassen"). Bis das Embedding-Modell feststeht, als benannte Konstante `EMBEDDING_DIM = 1024` zentralisieren und `Vector(EMBEDDING_DIM)` verwenden, damit eine spätere Änderung lokal bleibt.

## Umsetzungsschritte

- [ ] `Base(DeclarativeBase)` definieren und exportieren (für `env.py` aus DB-1).
- [ ] `Student`, `Teacher` modellieren (PII minimal halten — keine Zusatzfelder).
- [ ] `Class` (mit `teacher_id`-FK), `Enrollment` (composite PK `student_id`+`class_id`, beide `ON DELETE CASCADE`).
- [ ] `Subject` (mit `UniqueConstraint`/`unique=True` auf `key`), `Skill` (mit `UniqueConstraint(subject_id, key)`).
- [ ] `SkillEdge` (composite PK `from_skill`+`to_skill`+`kind`, beide FKs `ON DELETE CASCADE`, `kind` Default `prerequisite`).
- [ ] `ContentNote` (FK `skill_id`, Felder `source_path`, `prose`, `created_at`).
- [ ] `ContentEmbedding` mit `embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)` und `sidecar_query` optional.
- [ ] `Attempt`, `LearnerState` (composite PK), `TeacherNote` (mit optionalem `override_mastery`).
- [ ] Sparsame `relationship()`-Definitionen nur dort, wo Folge-Tasks sie brauchen (z. B. `Skill.subject`, `ContentEmbedding.note`) — nichts über das Schema hinaus erfinden.
- [ ] Autogenerate-Diff gegen DB-1 prüfen: keine Schemaänderung.

## Akzeptanzkriterien

- [ ] `models.py` deckt **alle 12 Tabellen** typisiert ab (`Mapped[...]`/`mapped_column`).
- [ ] Die `pgvector`-Spalte (`Vector`) funktioniert: ein `list[float]` lässt sich schreiben und zurücklesen.
- [ ] Zusammengesetzte PKs (`enrollments`, `learner_state`, `skill_edges`) und Unique-Constraints (`subjects.key`, `skills(subject_id, key)`) sind abgebildet.
- [ ] `alembic revision --autogenerate` erzeugt gegen DB-1 **keine** Schemaänderung (Modelle == Migration).

## Tests / Verifikation

```bash
cd apps/api
# Modelle == Migration? Diff muss leer sein:
uv run alembic revision --autogenerate -m "check-drift"
# Erwartung: erzeugte Datei enthält 'pass' in upgrade()/downgrade() (kein Diff) -> danach Datei wieder löschen

# ORM-Roundtrip inkl. Vector-Spalte:
uv run python -c "
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from its.config import settings
from its.db.models import Student, ContentNote, ContentEmbedding
e=create_engine(settings.database_url)
with Session(e) as s:
    st=Student(display_name='Demo', grade_level=8); s.add(st)
    note=ContentNote(source_path='x.md', prose='p'); s.add(note); s.flush()
    emb=ContentEmbedding(note_id=note.id, chunk='c', embedding=[0.0]*1024); s.add(emb)
    s.flush()
    print('ok', st.id, emb.id)
    s.rollback()
"
# Erwartung: 'ok <uuid> <uuid>' ohne Fehler
```

## Abhaengigkeiten

- **DB-1** (Voraussetzung): liefert das migrierte Schema; die Modelle müssen es 1:1 spiegeln (Autogenerate-Diff = leer).
- **Nachgelagert:** **DB-3** (Engine/Session importieren `Base`/Modelle), **DB-4** (Seed schreibt über die Modelle), **RET-2/3/5**, **LM-2 (Tracing)**, **MOCK-1 (Seeder)**, **CON-2 (Ingestion)** — alle bauen auf `db/models.py`.

## Definition of Done

- [ ] Akzeptanzkriterium aus `docs/03` §7 (DB-2: „`models.py` deckt alle Tabellen typisiert ab; `pgvector`-Spalte funktioniert") erfüllt.
- [ ] ORM-Roundtrip-Smoke (inkl. `Vector`) grün; Autogenerate-Diff leer.
- [ ] `uv`-only — keine `pip`-Aufrufe.
- [ ] Keine PII über das Schema hinaus eingeführt (P4).
- [ ] GitHub-Issue DB-2 geschlossen, E2-Epic-Checkliste aktualisiert.
