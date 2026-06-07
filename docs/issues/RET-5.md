## Ziel

Eine Funktion `prerequisites(session, skill_id, max_depth=5)` ermittelt ueber eine **rekursive CTE** auf `skill_edges` alle Voraussetzungs-Skills eines Skills (transitiv), mit Tiefenlimit gegen Zyklen und unbegrenzte Rekursion. Jeder Skill erscheint einmal mit seiner minimalen Tiefe.

## Kontext & Prinzipien

- **Tech-Stack-Entscheidung (`docs/00` Section 5):** Der Link-Graph ist eine `edges`-Tabelle + rekursive CTE — keine separate Graph-DB. "Obsidian-Links sind getypte Kanten; Graph quasi gratis." Eine echte Graph-DB erst bei gemessenem Engpass.
- **P7:** Eine Implementierung, flaches Modul `retrieval/` — keine Plugin-Naht.
- **Kein Personenbezug:** `skill_edges` ist Domaenen-/Content-Struktur, kein personenbezogenes Datum → keine RLS noetig (analog RET-2).
- **P9 (`uv`-only).**

## Zu erstellende/aendernde Dateien

- `apps/api/src/its/retrieval/graph.py` (neu) — Kernimplementierung.
- `tests/test_graph.py` (neu) — Integrationstest gegen den Seed-Skill-Graph.

## Schnittstellen & Signaturen

Referenz aus `docs/05-retrieval.md`, Abschnitt 5 — exakt zu reproduzieren:

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

Relevantes Schema (aus `docs/03-database.md`):

```sql
CREATE TABLE skill_edges (                 -- gerichteter Voraussetzungs-/Link-Graph
  from_skill uuid REFERENCES skills(id) ON DELETE CASCADE,
  to_skill   uuid REFERENCES skills(id) ON DELETE CASCADE,
  kind       text NOT NULL DEFAULT 'prerequisite',  -- prerequisite | related
  PRIMARY KEY (from_skill, to_skill, kind)
);
```

Seed-Graph (aus `docs/03-database.md`, DB-4): `linear-equations → complete-the-square → quadratic-formula`.

## Umsetzungsschritte

- [ ] `prerequisites` exakt wie oben implementieren; rekursive CTE mit `UNION ALL`.
- [ ] Tiefenlimit ueber `d.depth < :md` durchsetzen (Schutz gegen Zyklen und uebermaessige Tiefe).
- [ ] `kind = 'prerequisite'` in **beiden** Teilen der CTE filtern.
- [ ] `DISTINCT` + `min(depth)` + `ORDER BY depth`, damit jeder Skill einmal mit minimaler Tiefe erscheint.
- [ ] `skill_id`/`max_depth` per Bindparam (kein String-Format).
- [ ] `max_depth` validieren (`>= 1`), Default `5`.
- [ ] `ruff`-clean.

## Akzeptanzkriterien

- [ ] `prerequisites` liefert die transitiven Voraussetzungen via rekursiver CTE.
- [ ] Tiefenlimit greift; ein Zyklus fuehrt **nicht** zu Endlosrekursion (durch `depth < max_depth`).
- [ ] Jeder Skill erscheint genau einmal mit seiner **minimalen** Tiefe, sortiert nach Tiefe.
- [ ] Rueckgabe ist `list[dict]` mit `skill_id` und `depth`.

## Tests / Verifikation

```bash
cd apps/api
uv run pytest ../../tests/test_graph.py -q
```

Testaufbau (Integration, Test-DB; Seed-Graph aus DB-4 oder lokal im Test angelegt):
- Kette `linear-equations → complete-the-square → quadratic-formula` mit `kind='prerequisite'` seeden.
- `prerequisites(db, skill_id=<quadratic-formula>)` → liefert `complete-the-square` (depth 1) und `linear-equations` (depth 2), sortiert nach depth.
- Zyklus-Test: kuenstliche Kante zurueck einfuegen → Aufruf terminiert (kein Hang) und respektiert `max_depth`.
- `max_depth=1` → liefert nur die direkten Voraussetzungen.

## Abhaengigkeiten

- **DB-2** (`db/models.py` / `skill_edges`): liefert die Kanten-Tabelle, ueber die die CTE laeuft.
- **(implizit) DB-4** (Skill-Seed): liefert den Demo-Graph fuer einen aussagekraeftigen Test.
- **Nachgelagert:** E6/E8 ("naechster Schritt"/Voraussetzungs-Logik) und ggf. das Lehrer-Dashboard nutzen die Voraussetzungs-Pfade.

> Hinweis: zu entscheiden — `skill_edges.kind` kennt auch `'related'`; RET-5 traversiert laut Doc nur `'prerequisite'`. Ob eine zweite Funktion `related(...)` fuer verwandte Skills gebraucht wird, ist im Plan nicht festgelegt — vorerst nur `prerequisite`.

## Definition of Done

- [ ] Akzeptanzkriterien erfuellt.
- [ ] `tests/test_graph.py` gruen, inkl. Tiefenlimit-/Zyklus-Test.
- [ ] Kein externer LLM-Call → keine PII-Pruefung noetig.
- [ ] `uv`-only, keine `pip`-Aufrufe.
- [ ] GitHub-Issue RET-5 geschlossen, E4-Checkliste aktualisiert.
