# E5 — Content-Ingestion (Markdown-Vault) — Detailplanung

## 1. Scope & Zielbild

E5 baut die **Content-Ingestion** des ITS: aus einem kuratierten Obsidian-artigen Markdown-Vault (`content/`) wird das **Domain-Modell** in die *eine* Datenbank überführt — als Prosa-Notizen, Embedding-Chunks und Skill-/Notiz-Kanten. Das Zielbild ist eine reproduzierbare Pipeline:

```
content/**/*.md  ──parse──►  ParsedNote(prose, sidecar_queries, links)
                                  │
                                  ├─► content_notes      (Prosa OHNE Code)
                                  ├─► content_embeddings  (Chunk-Embedding + sidecar_query)
                                  └─► skill_edges          (aus [[wikilinks]])
```

Die **Kernregel** des Epics (verhindert schlechtes Retrieval, docs/05 §6.1): Codeblöcke (` ```sql `, ` ```cypher `) werden **nicht** mit-embeddet. SQL-Tokens verzerren den semantischen Vektor. Stattdessen wird nur die Prosa embeddet; die Query bleibt als **Sidecar-Metadatum** an der Notiz, abrufbar für eine spätere Eskalation auf eine strukturierte Live-Query (RET-2 nutzt das).

E5 liefert die Daten, die der **Semantic-Modus** (RET-2, Epic E4) und der **Graph-Traversal** (RET-5) auslesen. Ohne E5 ist die Vektorsuche leer. E5 ist Teil von **Milestone M2 — Retrieval & Content**.

Abgrenzung (NICHT in diesem Epic): Router, semantic/individual/population-Queries, Graph-CTE (alles E4); BKT/Grading (E6/E7); Agent-Loop (E8). E5 endet, sobald der Vault deterministisch in die DB geschrieben werden kann.

## 2. Task-Reihenfolge & Abhängigkeiten

```
FND-2 (uv-Projekt) ─────────────► CON-1 (Parser, reine Funktion)
                                       │
DB-2 (SQLAlchemy-Modelle) ─────────────┤
                                       ▼
                                  CON-2 (Ingestion-Pipeline: parse → notes → embeddings → edges)

CON-3 (Demo-Vault) ── unabhängig, kann parallel/zuerst (liefert Testfixtures für CON-1 & CON-2)
```

Empfohlene Bearbeitungsreihenfolge:
1. **CON-3** zuerst oder parallel — der Demo-Vault dient als Eingabe-Fixture für die Tests von CON-1 und CON-2 und hat keine Abhängigkeit.
2. **CON-1** (Parser) — reine Funktion, keine DB; sofort unit-testbar.
3. **CON-2** (Pipeline) — verdrahtet Parser (CON-1) + Modelle (DB-2) + Embedding-Client (docs/07) und schreibt in die DB.

Nachgelagert warten auf E5: **RET-2** (Semantic-Suche liest `content_embeddings`), **RET-5** (Graph-Traversal über `skill_edges`/Notiz-Kanten), indirekt der Agent-`retrieve`-Node (E8).

## 3. Feinere Sub-Task-Zerlegung (über die Issues hinaus)

**CON-1 (Parser):**
- 1a. Regex-Konstanten `FENCE`, `WIKILINK` exakt wie im Doc übernehmen.
- 1b. `ParsedNote`-Dataclass (prose, sidecar_queries, links).
- 1c. `parse_note(md)` — nur `sql`/`cypher`-Fences als Sidecar; alle Fences aus der Prosa entfernen; Wikilinks aus der **Prosa** ziehen (nicht aus den Codeblöcken).
- 1d. Edge-Cases: kein Fence, mehrere Fences, Fence ohne Sprach-Tag, Wikilink mit Alias `[[ziel|anzeige]]` (> Hinweis: Alias-Verhalten ist im Doc nicht spezifiziert).
- 1e. Optionales Frontmatter-Parsing (skill_key) — gehört konzeptionell zu CON-2, hier nur entscheiden, ob der Parser es schon liefert.

**CON-2 (Pipeline):**
- 2a. Datei-Discovery: `content/**/*.md` rekursiv finden, deterministisch sortieren.
- 2b. `skill_id`-Auflösung aus Frontmatter oder Pfad (z. B. `content/math/<skill-key>.md` → Lookup in `skills`).
- 2c. `content_notes`-Upsert (source_path als natürlicher Schlüssel → Idempotenz / Re-Ingestion).
- 2d. Chunking-Strategie (Absätze) — kleine, eigene Hilfsfunktion `chunk_prose()`.
- 2e. Embedding-Aufruf pro Chunk über den Embedding-Client (docs/07).
- 2f. `content_embeddings`-Insert (chunk, embedding, sidecar_query = erste passende Query).
- 2g. Link-Persistenz: Wikilink-Ziele in `skill_edges` (kind='related') bzw. Notiz-Kanten.
- 2h. CLI-Entrypoint (`uv run python -m its.content.ingest <pfad>`).
- 2i. Idempotenz/Reset-Strategie bei erneutem Lauf.

**CON-3 (Demo-Vault):**
- 3a. `content/math/quadratic-equations.md` exakt wie im Doc.
- 3b. Mindestens eine zweite verlinkte Notiz (`quadratic-formula.md`), damit eine Kante real entsteht und CON-2-Link-Persistenz testbar ist.
- 3c. Frontmatter-Konvention dokumentieren (skill_key), falls CON-2 darauf baut.

## 4. Zentrale Designentscheidungen (mit Begründung)

- **Prosa/Code-Trennung vor dem Embedding (P2-nah, Retrieval-Qualität):** Das Embedding sieht ausschließlich natürliche Sprache. Code-Tokens würden die Kosinus-Ähnlichkeit verzerren und semantische Treffer verschlechtern. Die Query überlebt als Sidecar — exakt das, was RET-2 für die Eskalation braucht.
- **Vektorsuche braucht keine RLS (P1-Begründung greift hier NICHT):** `content_notes`/`content_embeddings` sind geteiltes Lernmaterial ohne `student_id`. Es ist kein personenbezogenes Datum (docs/05 §2). Deshalb läuft die Ingestion über eine privilegierte Rolle und schreibt direkt; keine Schüler-Isolation nötig. Wichtig, dies bewusst zu dokumentieren, damit niemand fälschlich RLS „nachrüstet".
- **Embeddings über den zentralen `llm`-Client / Embedding-Funktion (P4/P8):** Lernmaterial ist zwar nicht PII, aber der Embedding-Pfad MUSS denselben Backend-Schalter (`settings.llm_backend`, local | frontier) respektieren wie der LLM-Client (docs/07), damit Datenresidenz (P8) zentral steuerbar bleibt. > Hinweis: docs/07 spezifiziert `complete()`, aber **keine** Embedding-Funktion — die Schnittstelle ist offen (siehe offene Fragen).
- **Idempotente Ingestion über `source_path`:** Re-Ingestion derselben Datei darf keine Duplikate erzeugen. `source_path` ist der natürliche Schlüssel; bei Re-Ingestion werden die Embeddings der Notiz ersetzt (ON DELETE CASCADE von `content_embeddings` an `content_notes`).
- **Vektordimension 1024 als Platzhalter:** Das Schema (docs/03) nutzt `vector(1024)` mit dem Kommentar „Dim an Modell anpassen". Die Pipeline darf die Dimension nicht hart annehmen, sondern aus der Embedding-Antwort ableiten / validieren.
- **`uv`-only (P9):** Discovery, Ausführung und Tests laufen ausschließlich über `uv run`. Kein `pip`.

## 5. Risiken & Gegenmaßnahmen

- **Regex-Fragilität beim Fence-Matching:** Verschachtelte/uneinheitliche Codeblöcke oder ` ``` ` in Inline-Code können den `FENCE`-Regex stören. → Gegenmaßnahme: Tests mit mehreren Fences, Fence ohne Sprach-Tag, Prosa mit Inline-Backticks; Doc-Regex unverändert übernehmen, aber Verhalten dokumentieren.
- **Falsch-positive Wikilinks aus Code:** Wikilinks werden bewusst nur aus der **Prosa** (nach Entfernen der Fences) extrahiert → vermeidet, dass `[[...]]` in einem SQL-Kommentar als Kante landet.
- **Embedding-Dimension ≠ Schema:** Liefert das gewählte Modell z. B. 768 statt 1024, schlägt der Insert fehl. → Dimension aus erster Antwort prüfen und gegen Schema validieren; klare Fehlermeldung.
- **Nicht-deterministische Ingestion:** Ungeordnete Datei-Discovery erschwert reproduzierbare Tests/Diffs. → Pfade deterministisch sortieren.
- **Datenresidenz beim Frontier-Embedding (P8):** Werden Prosa-Chunks an eine externe Embedding-API außerhalb CH/EU geschickt, ist das ein Compliance-Bruch — selbst wenn der Inhalt „nur" Lernmaterial ist. → Backend-Schalter respektieren; Default lokal.
- **Skill-Auflösung schlägt fehl:** Existiert der referenzierte `skill_key` nicht in `skills`, bleibt `content_notes.skill_id` NULL oder die Kante kann nicht angelegt werden. → Fehlende Skills loggen, Notiz trotzdem (mit `skill_id=NULL`) anlegen; Edge nur bei aufgelösten Endpunkten.

## 6. Offene Fragen / zu treffende Entscheidungen

1. **Embedding-Schnittstelle:** docs/07 definiert nur `complete()`. Es fehlt eine `embed(text) -> list[float]`-Funktion (Name, Modul, Backend-Verzweigung). Muss vor CON-2 festgelegt werden.
2. **Konkretes Embedding-Modell + Dimension:** Schema nutzt Platzhalter `vector(1024)`. Reales Modell und Dimension (lokal vs. frontier) bestimmen die Migration.
3. **Chunking-Strategie:** „nach Absätzen" ist grob. Min/Max-Chunkgröße, Overlap, Umgang mit Überschriften offen.
4. **Sidecar-Zuordnung bei mehreren Chunks:** Doc sagt „erste passende Query" — soll dieselbe Query an allen Chunks hängen oder nur am ersten? Offen.
5. **`skill_id`-Quelle:** Frontmatter-Feld vs. Pfadkonvention (`content/<subject>/<skill-key>.md`) — Konvention festlegen.
6. **Wikilink → Kantentyp:** `skill_edges.kind` ist `prerequisite|related`. Ein neutraler `[[wikilink]]` ist semantisch `related`; ob Notiz-Kanten in `skill_edges` oder einer separaten Notiz-Edge-Tabelle landen, ist nicht eindeutig (docs/00 erwähnt „Notiz-Kanten").
7. **Idempotenz/Reset:** Voller Re-Build vs. inkrementelles Upsert — Verhalten bei geänderter Datei festlegen.

## 7. Test-/Verifikationsstrategie für das Epic

- **Unit (CON-1, keine DB):** `tests/test_content_parser.py` (docs/10 §4 nennt diesen Test explizit). Prüft: Codeblock wird abgetrennt und ist **nicht** in `prose`; `sidecar_queries` enthält den SQL-Body; Wikilinks korrekt extrahiert; Wikilinks aus Codeblöcken erscheinen NICHT.
- **Integration (CON-2, gegen Test-DB):** Demo-Vault ingestieren → prüfen, dass `content_notes`-Zeile existiert (Prosa ohne ` ``` `), `content_embeddings`-Zeilen mit korrekter Dimension und gesetztem `sidecar_query`, und eine `skill_edges`/Notiz-Kante aus dem `[[quadratic-formula]]`-Link.
- **CON-3 (statisch):** Datei existiert, ist valides Markdown, enthält genau einen ` ```sql `-Block und mindestens einen `[[wikilink]]`; durchläuft `parse_note` ohne Verlust.
- **Befehle:** `uv run pytest tests/test_content_parser.py -q`; Pipeline-Integrationstest gegen die per Alembic migrierte Test-DB (Postgres + pgvector). Kein `pip` (P9), keine PII in externen Calls (P4) — Lernmaterial ist nicht PII, aber der Backend-Schalter wird respektiert.

