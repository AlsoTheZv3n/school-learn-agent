## Ziel

Ein eigenständiges, idempotentes Skript `scripts/import_production.py` importiert echtes Lernmaterial über die reguläre CON-2-Ingestion-Pipeline und echte Klassenlisten/Personen aus einer validierten Quelle (Pydantic) per Upsert über stabile externe Schlüssel. Mock- und Echtdaten werden niemals in derselben DB gemischt.

## Kontext & Prinzipien

- **P2 (kuratiert, keine LLM-Halluzination):** Echtes Material läuft durch dieselbe Ingestion wie Mock-Content — nur **Prosa** wird embeddet, der `sql`/`cypher`-Block wird als `sidecar_query` getrennt gehalten. Kein Sonderpfad fürs Embedding, damit der Bewertungs-/Erklärpfad konsistent bleibt.
- **P4 (PII raus):** Der Personen-Import schreibt PII (Anzeigename, Stufe) ausschliesslich in die DB; nichts davon geht roh an ein LLM. Das Schema ist bereits PII-minimal (docs/03).
- **P8 (CH/EU-Residenz):** Dieses Skript schreibt Echtdaten Minderjähriger und darf nur gegen die CH/EU-Prod-DB laufen (siehe PROD-3); der Guard (PROD-2) erzwingt `DATA_MODE=prod`.
- **P9 (`uv`-only):** Aufruf ausschliesslich über `uv run`, kein `pip`.

## Zu erstellende/ändernde Dateien

- `scripts/import_production.py` (neu) — der Import-Entrypoint.
- `apps/api/src/its/content/ingest.py` (bestehend, aus CON-2) — wird genutzt, nicht dupliziert.
- `apps/api/src/its/db/models.py` (bestehend, aus DB-2) — `Student`, `Class`, `Enrollment`, `ContentNote`, `ContentEmbedding` werden für den Upsert verwendet.
- ggf. neue Alembic-Migration unter `apps/api/.../db/migrations/` für eine `external_id`-Spalte (siehe Hinweis unten).
- `tests/test_import_production.py` (neu) — Idempotenz- und Content-Pfad-Tests.

## Schnittstellen & Signaturen

Skizze aus docs/11 (B.1), die hier vollständig implementiert wird:

```python
# scripts/import_production.py (Skizze)
import os, sys

def _require_prod():
    if os.environ.get("DATA_MODE") != "prod":
        sys.exit("REFUSED: import_production requires DATA_MODE=prod.")

def import_roster(path: str) -> None:
    _require_prod()
    # validiere Zeilen (Pydantic), upsert students/classes/enrollments anhand externer IDs
    ...

def import_content(vault_dir: str) -> None:
    _require_prod()
    # nutze its.content.ingest (CON-2) — gleiche Pipeline wie Mock-Content
    ...
```

Reguläre Ingestion (CON-2, docs/05) — Ablauf, der wiederverwendet wird:

```
1. Markdown-Datei lesen -> parse_note.
2. content_notes-Zeile anlegen (prose, source_path, ggf. skill_id).
3. Prosa chunken -> je Chunk Embedding -> content_embeddings mit sidecar_query.
4. Links als skill_edges/Note-Kanten persistieren.
```

Parser-Vertrag (CON-1, docs/05) — Codeblock wird NICHT mit-embeddet:

```python
@dataclass
class ParsedNote:
    prose: str                 # Markdown OHNE Codebloecke
    sidecar_queries: list[str] # extrahierte ```sql/```cypher-Bloecke
    links: list[str]           # Ziel-Notizen aus [[wikilinks]]

def parse_note(md: str) -> ParsedNote: ...
```

Relevante Modelle (DB-2, docs/03) für den Upsert:

```python
class Student(Base):
    __tablename__ = "students"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    display_name: Mapped[str]
    grade_level: Mapped[int]
```

Vorgeschlagene Pydantic-Validierung einer Roster-Zeile (autark, an docs/03-Felder angelehnt):

```python
from pydantic import BaseModel, Field

class RosterRow(BaseModel):
    external_id: str = Field(min_length=1)   # stabiler Schluessel aus der Schul-Quelle
    display_name: str = Field(min_length=1)
    grade_level: int = Field(ge=1, le=13)
    class_key: str = Field(min_length=1)     # stabiler Klassen-Schluessel
```

> Hinweis: zu entscheiden — das Schema in docs/03 hat **keine** `external_id`/`external_key`-Spalte auf `students`/`classes`. Für einen echten idempotenten Upsert ist eine Alembic-Migration nötig (Empfehlung: `students.external_id text UNIQUE`, `classes.external_key text UNIQUE`). Ohne stabilen Schlüssel kann Idempotenz nicht erfüllt werden.

## Umsetzungsschritte

- [ ] `scripts/import_production.py` mit `_require_prod()`-Guard zu Beginn jeder Public-Funktion anlegen.
- [ ] `RosterRow`-Pydantic-Modell definieren.
- [ ] CSV/Quelle einlesen, **jede** Zeile validieren; ungültige Zeilen mit Zeilennummer sammeln und am Ende melden (kein Teil-Commit bei Fehlern).
- [ ] Alembic-Migration für `external_id`/`external_key` (UNIQUE) ergänzen (siehe Hinweis).
- [ ] Upsert `students` über `external_id` (`INSERT ... ON CONFLICT (external_id) DO UPDATE` bzw. SQLAlchemy-Äquivalent).
- [ ] Upsert `classes` über `external_key`; `enrollments` über `(student_id, class_id)`-PK idempotent setzen.
- [ ] `import_content(vault_dir)` implementieren: Vault rekursiv durchlaufen, je `.md` `its.content.ingest` aufrufen; Idempotenz über `content_notes.source_path` (kein erneutes Embedden bei unverändertem Pfad).
- [ ] CLI-Argumente `--roster <path>` und `--vault <dir>` + `__main__`-Block als `uv`-Entrypoint.
- [ ] Optional `--dry-run` (validieren ohne Schreiben).
- [ ] Alles in einer DB-Transaktion pro Importlauf, Rollback bei Fehler.
- [ ] Klarstellen (Docstring/README), dass dieses Skript niemals Mock-Daten erzeugt.

## Akzeptanzkriterien

- [ ] Echtes Material läuft über die **reguläre** CON-2-Pipeline (kein Sonderpfad fürs Embedding); nur Prosa wird embeddet, `sidecar_query` getrennt gespeichert.
- [ ] Personen-Import ist **idempotent** (zweimaliger Lauf desselben Rosters erzeugt keine Duplikate).
- [ ] Import ist klar von Mock getrennt (eigenes Skript, `_require_prod()`-Guard).
- [ ] Roster-Zeilen werden per Pydantic validiert; ungültige Zeilen werden gemeldet, kein Teil-Commit.
- [ ] Aufruf ausschliesslich über `uv run`; keine `pip`-Nutzung.

## Tests / Verifikation

- [ ] `cd apps/api; $env:DATA_MODE='mock'; uv run python ../../scripts/import_production.py --roster x.csv` → Exit mit Meldung `REFUSED: import_production requires DATA_MODE=prod.` (Guard greift).
- [ ] Idempotenz: `$env:DATA_MODE='prod'; uv run python ../../scripts/import_production.py --roster sample.csv` zweimal gegen Test-DB → `SELECT count(*) FROM students` ist nach beiden Läufen identisch.
- [ ] Content: `uv run python ../../scripts/import_production.py --vault content/math` → `content_notes` + `content_embeddings` angelegt; ein Chunk enthält **keine** SQL-Tokens; `sidecar_query` ist gesetzt.
- [ ] `uv run pytest tests/test_import_production.py -q` → grün.

## Abhängigkeiten

- **CON-2** — liefert `its.content.ingest`; PROD-1 nutzt diese Pipeline unverändert für echten Content.
- **DB-2** — liefert die SQLAlchemy-Modelle (`Student`, `Class`, `Enrollment`, `ContentNote`, `ContentEmbedding`) für den Upsert.
- Nachgelagert: **PROD-2** baut auf dem `_require_prod()`-Guard dieses Skripts auf und prüft beide Guard-Richtungen gemeinsam.

## Definition of Done

- [ ] Akzeptanzkriterien (oben, abgeleitet aus docs/11 B.1) erfüllt.
- [ ] Tests grün via `uv run pytest`; Safety-relevante Pfade (Guard) durch Test belegt.
- [ ] Keine PII in externen LLM-Prompts (Personen-Import schreibt nur in die DB; Content-Embedding läuft über die anonymisierungsbewusste CON-2/LLM-Naht).
- [ ] `uv`-only, keine `pip`-Aufrufe.
- [ ] Zugehöriges GitHub-Issue PROD-1 geschlossen, E14-Epic-Checkliste aktualisiert.
