## Ziel

Eine Ingestion-Pipeline liest die Markdown-Dateien des Vaults, legt pro Datei eine `content_notes`-Zeile (Prosa **ohne** Code) an, embeddet **ausschließlich** die Prosa chunk-weise nach `content_embeddings` (mit der ` ```sql `-Query als `sidecar_query`) und persistiert die `[[wikilinks]]` als Kanten. Danach ist der Semantic-Modus (RET-2) mit echten Daten bedienbar.

## Kontext & Prinzipien

- **Retrieval-Qualität (Kernregel, docs/05 §6.1/§6.2):** Es wird **nur Prosa** embeddet; die Query wird getrennt als `sidecar_query` gespeichert. Das ist das zentrale AK dieses Tasks und der Grund, warum der Parser (CON-1) vorgeschaltet ist.
- **P8 (Datenresidenz CH/EU):** Der Embedding-Aufruf läuft über den zentralen Backend-Schalter (`settings.llm_backend`, `local | frontier`). Selbst wenn Lernmaterial kein PII ist, dürfen Prosa-Chunks nicht unkontrolliert an eine API außerhalb CH/EU gehen — Default ist `local`.
- **P9 (`uv` ausschliesslich):** Discovery, Pipeline-Lauf und Tests laufen über `uv run`; kein `pip`.

> Hinweis: P1/RLS ist hier NICHT relevant — `content_notes`/`content_embeddings` sind geteiltes Lernmaterial ohne `student_id` (docs/05 §2). Die Pipeline schreibt über eine privilegierte Rolle; es wird **keine** Schüler-Isolation nachgerüstet.

## Zu erstellende/ändernde Dateien

- `apps/api/src/its/content/ingest.py` — die Pipeline (gemäß Repo-Layout docs/00 §6: `content/ ... ingest.py`).
- `tests/test_content_ingest.py` — Integrationstest gegen die migrierte Test-DB (neu; nicht namentlich im Doc, aber zur Verifikation der AK nötig).
- (Nutzt vorhandene Modelle aus `apps/api/src/its/db/models.py` — DB-2 — sowie `apps/api/src/its/content/parser.py` — CON-1.)

## Schnittstellen & Signaturen

Ablauf laut docs/05 §6.2:

```
1. Markdown-Datei lesen → parse_note.
2. content_notes-Zeile anlegen (prose, source_path, ggf. skill_id aus Frontmatter/Pfad).
3. Prosa chunken (z. B. nach Absätzen) → je Chunk Embedding berechnen (llm-Client, docs/07)
   → content_embeddings mit sidecar_query (erste passende Query) speichern.
4. Links als skill_edges/Note-Kanten persistieren.
```

Parser-Schnittstelle (aus CON-1, autark reproduziert):

```python
@dataclass
class ParsedNote:
    prose: str
    sidecar_queries: list[str]
    links: list[str]

def parse_note(md: str) -> ParsedNote: ...
```

Relevante Modelle/DDL (aus docs/03):

```python
class ContentEmbedding(Base):
    __tablename__ = "content_embeddings"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    note_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("content_notes.id", ondelete="CASCADE"))
    chunk: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1024), nullable=False)  # Dim an Modell anpassen
    sidecar_query: Mapped[str | None] = mapped_column(Text)
```

```sql
CREATE TABLE content_notes (
  id          uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  skill_id    uuid REFERENCES skills(id),
  source_path text NOT NULL,               -- Pfad im Vault
  prose       text NOT NULL,               -- Prosa OHNE Codeblöcke
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE content_embeddings (
  id            uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  note_id       uuid REFERENCES content_notes(id) ON DELETE CASCADE,
  chunk         text NOT NULL,
  embedding     vector(1024) NOT NULL,      -- Dim an Modell anpassen
  sidecar_query text                        -- abgetrennter ```sql-Block
);
CREATE INDEX ON content_embeddings USING hnsw (embedding vector_cosine_ops);
CREATE TABLE skill_edges (                  -- gerichteter Voraussetzungs-/Link-Graph
  from_skill uuid REFERENCES skills(id) ON DELETE CASCADE,
  to_skill   uuid REFERENCES skills(id) ON DELETE CASCADE,
  kind       text NOT NULL DEFAULT 'prerequisite',  -- prerequisite | related
  PRIMARY KEY (from_skill, to_skill, kind)
);
```

Backend-Schalter (aus docs/02 / docs/07 — der Embedding-Pfad muss ihn respektieren):

```python
# settings.llm_backend == "local" | "frontier"  (its/config.py)
# its/llm/client.py kapselt das Backend; complete(system,user) existiert dort bereits.
```

> Hinweis: zu entscheiden — docs/07 spezifiziert `complete()`, aber **keine** Embedding-Funktion. Es muss eine `embed(text) -> list[float]` (Name/Modul/Backend-Verzweigung) festgelegt werden, bevor CON-2 final ist. Bis dahin sollte die Pipeline eine klar benannte, injizierbare Embedding-Funktion erwarten (z. B. Parameter `embed_fn`), damit der Test sie mocken kann.

## Umsetzungsschritte

- [ ] `ingest.py` anlegen; eine Funktion `ingest_path(session, root, *, embed_fn)` (oder analog) entwerfen, die einen Vault-Pfad rekursiv verarbeitet.
- [ ] Datei-Discovery: `*.md` rekursiv finden und **deterministisch sortieren** (reproduzierbare Läufe/Tests).
- [ ] Pro Datei: Inhalt lesen → `parse_note(md)` (CON-1).
- [ ] `skill_id` auflösen: aus Frontmatter-Feld `skill_key` oder Pfadkonvention `content/<subject>/<skill-key>.md` → Lookup in `skills`. Fehlt der Skill: loggen, `content_notes.skill_id = NULL` setzen, Notiz trotzdem anlegen.
- [ ] `content_notes`-Zeile mit `prose`, `source_path` (relativ, stabil) und ggf. `skill_id` anlegen — idempotent über `source_path` (vorhandene Notiz + ihre Embeddings ersetzen).
- [ ] Prosa chunken (`chunk_prose()` — z. B. nach Leerzeilen/Absätzen); leere Chunks verwerfen.
- [ ] Pro Chunk Embedding via `embed_fn` berechnen; Dimension gegen das Schema (Vector-Spalte) validieren und bei Abweichung mit klarer Meldung abbrechen.
- [ ] `content_embeddings` schreiben: `chunk`, `embedding`, `sidecar_query` = erste passende Query aus `parsed.sidecar_queries` (oder `None`).
- [ ] Links persistieren: für jedes `[[ziel]]` eine Kante anlegen (Ziel-Skill/Notiz auflösen; `kind='related'`). Kante nur bei aufgelösten Endpunkten; fehlende Ziele loggen.
- [ ] CLI-Entrypoint ergänzen (`python -m its.content.ingest <pfad>`), der eine privilegierte Session öffnet und `ingest_path` aufruft.
- [ ] `tests/test_content_ingest.py` schreiben (siehe Tests).
- [ ] Ruff über das neue Modul.

> Hinweis: zu entscheiden — (a) ob `sidecar_query` an **allen** Chunks oder nur am ersten hängt (Doc: „erste passende Query"); (b) ob Notiz-Links in `skill_edges` oder einer separaten Notiz-Edge-Tabelle landen (docs/00 erwähnt „Notiz-Kanten", Schema kennt nur `skill_edges`).

## Akzeptanzkriterien

- [ ] Es wird **nur Prosa** embeddet; in keinem `content_embeddings.chunk` steht ein ` ```sql `-Block (docs/05 §6.2/§7: „Ingestion embeddet nur Prosa, Query als Sidecar (CON-2)").
- [ ] `content_embeddings.sidecar_query` enthält die abgetrennte Query getrennt von der Prosa.
- [ ] Pro ingestierter Datei existiert genau eine `content_notes`-Zeile (idempotent bei Re-Ingestion über `source_path`).
- [ ] `[[wikilinks]]` werden als Kanten persistiert (mind. die Demo-Kante zu `quadratic-formula`).
- [ ] Die Embedding-Dimension entspricht der `Vector(...)`-Spaltendefinition.

## Tests / Verifikation

Voraussetzung: Test-DB läuft (Postgres + pgvector), Alembic `upgrade head` angewandt.

```bash
cd apps/api
uv run pytest ../../tests/test_content_ingest.py -q
```

Erwartete Assertions (mit gemocktem/festem `embed_fn`, das einen 1024-dim Vektor liefert):

```python
# nach ingest_path(session, demo_vault, embed_fn=fake_embed):
#  - genau 1 content_notes-Zeile für quadratic-equations.md, prose enthält kein '```'
#  - >=1 content_embeddings-Zeile, KEIN chunk enthält 'SELECT', sidecar_query enthält 'SELECT avg(mastery)'
#  - >=1 skill_edges-/Note-Kante mit Ziel 'quadratic-formula'
```

Manuelle Verifikation (optional):

```bash
cd apps/api
uv run python -m its.content.ingest ../../content
# erwartete Log-Ausgabe: Anzahl Notizen/Chunks/Kanten; keine Tracebacks
```

## Abhängigkeiten

- **CON-1** (Parser): liefert `parse_note`/`ParsedNote` für die Prosa/Code-Trennung — ohne ihn würden Code-Tokens mit-embeddet.
- **DB-2** (SQLAlchemy-Modelle): liefert `ContentNote`, `ContentEmbedding`, `SkillEdge`, in die geschrieben wird, sowie die `Vector`-Spalte.
- **Nachgelagert:** **RET-2** (Semantic-Suche) liest die hier erzeugten `content_embeddings`; **RET-5** (Graph) nutzt die erzeugten Kanten.

## Definition of Done

- [ ] Akzeptanzkriterien aus docs/05 §7 (CON-2) erfüllt — insbesondere „nur Prosa embeddet, Query als Sidecar".
- [ ] Tests grün (Integrationstest gegen migrierte Test-DB); Safety-Tests nicht betroffen (kein `student_id`-Pfad).
- [ ] Keine PII in externen LLM/Embedding-Prompts: Lernmaterial ist nicht PII, aber der Backend-Schalter (`settings.llm_backend`, Default `local`) wird respektiert (P8).
- [ ] `uv`-only, keine `pip`-Aufrufe.
- [ ] Zugehöriges GitHub-Issue (CON-2) geschlossen, E5-Epic-Checkliste aktualisiert.
