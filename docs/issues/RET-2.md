## Ziel

Eine `pgvector`-Aehnlichkeitssuche `semantic_search(session, query_embedding, k)` ueber die Tabelle `content_embeddings` liefert die `k` aehnlichsten **Prosa-Chunks** plus die zugeordneten **Sidecar-Query-Metadaten** und die `skill_id` — geteiltes, skalenfreies Lernmaterial fuer eine moegliche Eskalation auf eine Live-Query.

## Kontext & Prinzipien

- **Geteiltes, skalenfreies Wissen (P-Modi, `docs/00` Section 3):** Erklaerendes Wissen ist fuer eine:n oder eine Million Lernende identisch — einmal ablegen, geteilt nutzen. `content_embeddings`/`content_notes` tragen **keinen** `student_id`.
- **P1 / kein RLS hier:** Dies ist Lernmaterial, kein personenbezogenes Datum. Daher braucht RET-2 **keine** gescopte Session und keine RLS — bewusst, im Gegensatz zu RET-3/RET-4.
- **E5-Kernregel (Ingestion, CON-2):** RET-2 verlaesst sich darauf, dass **nur Prosa** embeddet wurde und SQL-Bloecke getrennt als `sidecar_query` liegen. Wuerde Code mit-embeddet, verzerrten SQL-Tokens den Vektor und das Retrieval wuerde schlecht.
- **P8 (CH/EU-Residenz):** Embeddings liegen in der Projekt-DB (CH/EU); RET-2 ruft kein externes LLM auf — es nimmt einen fertigen Vektor entgegen.
- **P9 (`uv`-only).**

## Zu erstellende/aendernde Dateien

- `apps/api/src/its/retrieval/semantic.py` (neu) — Kernimplementierung.
- `tests/test_semantic.py` (neu) — Integrationstest gegen Test-DB mit eingespielten Embeddings.

## Schnittstellen & Signaturen

Referenz aus `docs/05-retrieval.md`, Abschnitt 2 — exakt zu reproduzieren:

```python
from sqlalchemy import text
from sqlalchemy.orm import Session

def semantic_search(session: Session, query_embedding: list[float], k: int = 5):
    rows = session.execute(text("""
        SELECT ce.chunk, ce.sidecar_query, cn.skill_id
        FROM content_embeddings ce
        JOIN content_notes cn ON cn.id = ce.note_id
        ORDER BY ce.embedding <=> :q       -- Kosinus-Distanz (HNSW)
        LIMIT :k
    """).bindparams(q=str(query_embedding), k=k))
    return [dict(r._mapping) for r in rows]
```

Relevantes Schema (aus `docs/03-database.md`, Abschnitt 3) — Kontext fuer die Query:

```sql
CREATE TABLE content_notes (
  id          uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  skill_id    uuid REFERENCES skills(id),
  source_path text NOT NULL,
  prose       text NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE content_embeddings (
  id            uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  note_id       uuid REFERENCES content_notes(id) ON DELETE CASCADE,
  chunk         text NOT NULL,
  embedding     vector(1024) NOT NULL,        -- Dim an Modell anpassen
  sidecar_query text
);
CREATE INDEX ON content_embeddings USING hnsw (embedding vector_cosine_ops);
```

SQLAlchemy-Modell (aus `docs/03-database.md`, DB-2):

```python
from pgvector.sqlalchemy import Vector
class ContentEmbedding(Base):
    __tablename__ = "content_embeddings"
    embedding: Mapped[list[float]] = mapped_column(Vector(1024), nullable=False)
    chunk: Mapped[str] = mapped_column(Text, nullable=False)
    sidecar_query: Mapped[str | None] = mapped_column(Text)
```

## Umsetzungsschritte

- [ ] `semantic_search` exakt wie oben implementieren; HNSW-Index + Kosinus-Distanzoperator `<=>` nutzen.
- [ ] Vektor als Bindparam uebergeben (`q=str(query_embedding)`) — kein String-Format direkt in die Query (Injection-Schutz).
- [ ] `k` validieren (`k > 0`), Default `5`.
- [ ] Eingabe `query_embedding` als `list[float]` typisieren; defensiver Check, dass es keine leere Liste ist.
- [ ] Rueckgabe als `list[dict]` mit Schluesseln `chunk`, `sidecar_query`, `skill_id`.
- [ ] **Wichtig:** Das Query-Embedding wird **nicht** in diesem Modul berechnet — RET-2 nimmt den fertigen Vektor entgegen. Die Berechnung gehoert zum LLM-Client (`docs/07`).
- [ ] `ruff`-clean.

## Akzeptanzkriterien

- [ ] `semantic_search` nutzt HNSW/Kosinus (`<=>`) und gibt die `k` aehnlichsten Chunks zurueck.
- [ ] Jede Ergebniszeile enthaelt `chunk`, `sidecar_query` (kann `None` sein) und `skill_id`.
- [ ] Der Vektor wird per Bindparam uebergeben (keine String-Interpolation in SQL).
- [ ] Keine `student_id`-Bindung, keine RLS-Session noetig (geteiltes Material).

## Tests / Verifikation

```bash
cd apps/api
uv run pytest ../../tests/test_semantic.py -q
```

Testaufbau (Integration, echtes Postgres mit pgvector; Fixtures aus `docs/10` `conftest.py`):
- Eine `content_notes`-Zeile + zwei `content_embeddings` mit unterschiedlichen Vektoren einfuegen (manuell, bis CON-2 verfuegbar ist).
- `semantic_search(db, query_embedding=<naeher an Embedding A>, k=1)` → liefert Chunk A.
- Rueckgabe enthaelt `sidecar_query` (z. B. der `SELECT avg(mastery) ...`-Block aus dem Demo-Vault) und `skill_id`.

> Hinweis: zu entscheiden — die Vektordimension ist im Schema Platzhalter `vector(1024)` und vom finalen Embedding-Modell abhaengig. Der Test muss die reale Dimension treffen; Dimension nicht im Test hartcodieren, sondern aus Schema/Settings ableiten.
> Hinweis: zu entscheiden — solange CON-2 noch nicht eingespielt hat, koennen die Test-Embeddings nur manuell gesetzt werden; den Test ggf. bis CON-2 markieren.

## Abhaengigkeiten

- **DB-2** (`db/models.py`): liefert `ContentEmbedding`/`ContentNote` und die `Vector`-Spalte plus den HNSW-Index, gegen die diese Query laeuft.
- **CON-2** (Ingestion, `docs/05` Abschnitt 6.2): fuellt `content_notes`/`content_embeddings` mit nur-Prosa-Embeddings und getrennten Sidecar-Queries — ohne das liefert RET-2 nichts Sinnvolles und der End-to-End-Test ist nicht moeglich.
- **Nachgelagert:** AG-2 (`agent/nodes/retrieve.py`, `docs/07`) ruft `semantic_search` im SEMANTIC-Pfad auf.

## Definition of Done

- [ ] Akzeptanzkriterien erfuellt.
- [ ] `tests/test_semantic.py` gruen (gegen echtes Postgres mit pgvector).
- [ ] Kein externer LLM-Call in diesem Modul → PII-Pruefung nicht betroffen (Embedding kommt von aussen).
- [ ] `uv`-only, keine `pip`-Aufrufe.
- [ ] GitHub-Issue RET-2 geschlossen, E4-Checkliste aktualisiert.
