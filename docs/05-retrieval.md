# 05 — Retrieval & Content-Ingestion (E4, E5, M2)

**Ziel:** Der Router und die drei Modi aus *einer* DB, der Graph-Traversal per CTE, und die
Vault-Ingestion mit Prosa/Code-Trennung.

**Voraussetzungen:** SAF-2, SAF-3 (Scoping/Cohort), DB-2 (Modelle), FND-2.
**Issues:** RET-1 … RET-5, CON-1 … CON-3.

---

## 1. Router (RET-1)

Entscheidet pro Anfrage **Scope** (semantic/individual/population) und ob eine Eskalation auf
eine **Live-Query** nötig ist. Die Entscheidung wird geloggt (auditierbar, P6).

`apps/api/src/its/retrieval/router.py`:

```python
from dataclasses import dataclass
from enum import StrEnum

class Mode(StrEnum):
    SEMANTIC = "semantic"
    INDIVIDUAL = "individual"
    POPULATION = "population"

@dataclass(frozen=True)
class RouteDecision:
    mode: Mode
    escalate_to_query: bool   # True = strukturierte Live-Query statt nur Prosa
    reason: str               # Begründung (Logging/Audit)

def route(question: str, *, has_student_scope: bool) -> RouteDecision:
    """Heuristik/Klassifikation. Start: regelbasiert; später Klassifikator.
    - Aggregat-/Vergleichsbegriffe ("Klasse", "Durchschnitt", "alle") -> POPULATION
    - Personenbezug auf den Lernenden ("mein Stand", "wo stehe ich") -> INDIVIDUAL
    - sonst erklärend -> SEMANTIC
    Eskalation, wenn frische/präzise Zahlen verlangt werden."""
    ...
```

> Anfangs bewusst regelbasiert halten. Erst wenn nötig durch einen kleinen Klassifikator
> ersetzen — der explizite `RouteDecision.reason` bleibt erhalten.

---

## 2. Semantic-Modus (RET-2)

`pgvector`-Ähnlichkeitssuche über `content_embeddings`. Gibt Prosa-Chunks **plus** die
zugeordneten Sidecar-Query-Metadaten zurück (für eine mögliche Eskalation).

`apps/api/src/its/retrieval/semantic.py`:

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

> Geteiltes, skalenfreies Wissen (P-Modi). Kein `student_id`-Bezug, keine RLS nötig — das ist
> Lernmaterial, kein personenbezogenes Datum.

---

## 3. Individual-Modus (RET-3) · `safety-critical`

Immer auf **einen** `student_id` gescoped — über `require_student_scope` (SAF-2) und die
RLS-geschützte Session. Niemals ohne Scope ausführbar.

`apps/api/src/its/retrieval/individual.py`:

```python
from sqlalchemy import text
from sqlalchemy.orm import Session
from its.safety.scoping import require_student_scope
from its.auth.deps import Principal

def mastery_overview(session: Session, principal: Principal):
    sid = require_student_scope(principal)   # fail-closed
    rows = session.execute(text("""
        SELECT ls.skill_id, s.name, ls.mastery, ls.uncertainty, ls.attempts_count
        FROM learner_state ls JOIN skills s ON s.id = ls.skill_id
        WHERE ls.student_id = :sid
        ORDER BY s.name
    """).bindparams(sid=sid))
    return [dict(r._mapping) for r in rows]
```

> Doppelte Absicherung: `require_student_scope` *und* RLS. Selbst wenn der Code den Filter
> vergässe, verweigert RLS fremde Zeilen.

---

## 4. Population-Modus (RET-4) · `safety-critical`

`GROUP BY`-Aggregate **ausschliesslich** durch `enforce_min_cohort` (SAF-3).

`apps/api/src/its/retrieval/population.py`:

```python
from sqlalchemy import text
from sqlalchemy.orm import Session
from its.safety.cohort import enforce_min_cohort

def skill_mastery_distribution(session: Session, class_id: str, skill_id: str):
    row = session.execute(text("""
        SELECT count(*) AS n, avg(ls.mastery) AS avg_mastery
        FROM learner_state ls
        JOIN enrollments e ON e.student_id = ls.student_id
        WHERE e.class_id = :cid AND ls.skill_id = :skid
    """).bindparams(cid=class_id, skid=skill_id)).one()
    return enforce_min_cohort(
        n=int(row.n),
        payload={"avg_mastery": round(float(row.avg_mastery or 0.0), 3)},
    )
```

> Soft-Kohorten via Vektor-Ähnlichkeit („Lernende wie diese:r") sind möglich, aber das
> **Aggregat** läuft trotzdem durch die harte Schwelle.

---

## 5. Graph-Traversal (RET-5)

Rekursive CTE über `skill_edges` (Voraussetzungen/verwandte Skills). Tiefenlimit gegen Zyklen/Tiefe.

`apps/api/src/its/retrieval/graph.py`:

```python
from sqlalchemy import text
from sqlalchemy.orm import Session

def prerequisites(session: Session, skill_id: str, max_depth: int = 5):
    rows = session.execute(text("""
        WITH RECURSIVE deps(skill_id, depth) AS (
            SELECT from_skill, 1 FROM skill_edges
              WHERE to_skill = :sid AND kind = 'prerequisite'
            UNION ALL
            SELECT se.from_skill, d.depth + 1
              FROM skill_edges se JOIN deps d ON se.to_skill = d.skill_id
              WHERE se.kind = 'prerequisite' AND d.depth < :md
        )
        SELECT DISTINCT skill_id, min(depth) AS depth FROM deps GROUP BY skill_id ORDER BY depth
    """).bindparams(sid=skill_id, md=max_depth))
    return [dict(r._mapping) for r in rows]
```

> Der Obsidian-`[[wikilink]]`-Graph wird identisch behandelt (Notiz-Kanten); kein separater
> Graph-Store, solange die Tiefe gemessen unkritisch bleibt.

---

## 6. Content-Ingestion (E5)

### 6.1 Parser (CON-1) — Prosa/Code-Trennung

`apps/api/src/its/content/parser.py`:

```python
import re
from dataclasses import dataclass

FENCE = re.compile(r"```(\w+)?\n(.*?)```", re.DOTALL)
WIKILINK = re.compile(r"\[\[([^\]]+)\]\]")

@dataclass
class ParsedNote:
    prose: str                 # Markdown OHNE Codeblöcke
    sidecar_queries: list[str] # extrahierte ```sql/```cypher-Blöcke
    links: list[str]           # Ziel-Notizen aus [[wikilinks]]

def parse_note(md: str) -> ParsedNote:
    queries = [body.strip() for lang, body in FENCE.findall(md) if (lang or "").lower() in {"sql","cypher"}]
    prose = FENCE.sub("", md).strip()          # Codeblöcke entfernen -> Embedding sauber
    links = WIKILINK.findall(prose)
    return ParsedNote(prose=prose, sidecar_queries=queries, links=links)
```

> **Kernregel (verhindert schlechtes Retrieval):** Der Codeblock wird **nicht** mit-embeddet.
> SQL-Tokens verzerren den Vektor. Prosa embedden, Query als Sidecar-Metadatum halten.

### 6.2 Ingestion-Pipeline (CON-2)

`apps/api/src/its/content/ingest.py` (Ablauf):

1. Markdown-Datei lesen → `parse_note`.
2. `content_notes`-Zeile anlegen (`prose`, `source_path`, ggf. `skill_id` aus Frontmatter/Pfad).
3. Prosa chunken (z. B. nach Absätzen) → je Chunk Embedding berechnen (`llm`-Client, docs/07)
   → `content_embeddings` mit `sidecar_query` (erste passende Query) speichern.
4. Links als `skill_edges`/Note-Kanten persistieren.

**AK:** Es wird **nur Prosa** embeddet; `sidecar_query` getrennt gespeichert; Links als Kanten.

### 6.3 Demo-Vault (CON-3)

`content/math/quadratic-equations.md`:

````markdown
# Quadratische Ergänzung

Die quadratische Ergänzung formt ein Polynom in ein vollständiges Quadrat plus Restterm um.
Sie ist die Grundlage der quadratischen Lösungsformel. Verwandt: [[quadratic-formula]].

```sql
-- frische Detailzahl bei Bedarf (Sidecar, NICHT mit-embeddet)
SELECT avg(mastery) FROM learner_state ls
JOIN skills s ON s.id = ls.skill_id
WHERE s.key = 'complete-the-square';
```
````

---

## 7. Akzeptanzkriterien (gesamt)

- [ ] `router.route()` liefert `RouteDecision` mit Begründung; geloggt (RET-1)
- [ ] `semantic_search` per HNSW/Kosinus; gibt Prosa + Sidecar zurück (RET-2)
- [ ] `individual`-Query nur mit aufgelöstem Scope; doppelt durch RLS gesichert (RET-3)
- [ ] `population`-Aggregat ausschliesslich via `enforce_min_cohort` (RET-4)
- [ ] `prerequisites` rekursive CTE mit Tiefenlimit (RET-5)
- [ ] Parser trennt Prosa/Code + extrahiert Links (CON-1)
- [ ] Ingestion embeddet nur Prosa, Query als Sidecar (CON-2)
- [ ] Demo-Vault vorhanden (CON-3)

---

## Claude-Code-Prompt

```
Setze E4 + E5 (docs/05-retrieval.md) um: retrieval/router.py (RouteDecision mit reason),
retrieval/semantic.py (pgvector HNSW), retrieval/individual.py (Scope via require_student_scope,
zusätzlich RLS), retrieval/population.py (nur via enforce_min_cohort), retrieval/graph.py
(rekursive CTE, Tiefenlimit). Dann content/parser.py (Prosa/Code-Trennung + Wikilinks),
content/ingest.py (nur Prosa embedden, Query als Sidecar) und den Demo-Vault unter content/math/.
Schreibe Unit-Tests: Parser trennt Code korrekt ab; Population-Query verweigert kleine Kohorten.
Schliesse RET-1..5 und CON-1..3.
```
