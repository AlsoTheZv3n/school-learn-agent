## Ziel

Eine reine Parser-Funktion `parse_note(md)` trennt aus einer Markdown-Notiz die **Prosa** (ohne Codeblöcke) von den eingebetteten ` ```sql `/` ```cypher `-Blöcken (als „Sidecar-Queries") und extrahiert alle `[[wikilink]]`-Ziele. Damit sieht der spätere Embedding-Schritt ausschließlich sauberen Fließtext.

## Kontext & Prinzipien

- **P2 (Kuratierte Antworten / generative Freiheit nur wo Fehler sichtbar):** Der Parser arbeitet deterministisch und regelbasiert (Regex) — kein LLM. Die Prosa/Code-Trennung ist die strukturelle Voraussetzung dafür, dass kuratiertes Material sauber abgelegt wird, statt dass ein Modell rät, was Erklärung und was Query ist.
- **Retrieval-Qualität (Kernregel des Epics):** Der Codeblock wird **nicht** mit-embeddet — SQL-Tokens verzerren den semantischen Vektor und verschlechtern die Kosinus-Treffer. Deshalb muss der Parser den Code **vollständig** aus der Prosa entfernen und separat als Sidecar bereitstellen.
- **P9 (`uv` ausschliesslich):** Tests und Ausführung laufen über `uv run`, nie über `pip`.

> Hinweis: RLS/P1 ist hier bewusst NICHT relevant — der Parser ist eine reine Funktion ohne DB- und ohne `student_id`-Bezug. Lernmaterial ist kein personenbezogenes Datum.

## Zu erstellende/ändernde Dateien

- `apps/api/src/its/content/parser.py` — die Parser-Funktion und ihre Datenklasse (gemäß Repo-Layout docs/00 §6: `content/ parser.py (Prosa/Code-Split), ingest.py`).
- `tests/test_content_parser.py` — Unit-Tests (Prosa/Code-Trennung, Wikilink-Extraktion). In docs/10 §4 explizit als geforderter Test genannt.

## Schnittstellen & Signaturen

Referenzimplementierung aus docs/05 §6.1 (autark reproduziert):

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

Beispiel-Eingabe (aus dem Demo-Vault, CON-3), an der das Verhalten geprüft wird:

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

## Umsetzungsschritte

- [ ] Modul `apps/api/src/its/content/parser.py` anlegen (Paket `content/` ggf. mit `__init__.py`).
- [ ] Regex-Konstanten `FENCE` und `WIKILINK` exakt wie in der Referenz übernehmen.
- [ ] `ParsedNote`-Dataclass mit den Feldern `prose`, `sidecar_queries`, `links` definieren.
- [ ] `parse_note(md)` implementieren: nur ` ```sql `/` ```cypher `-Blöcke als Sidecar (Sprach-Tag case-insensitive); **alle** Fences aus der Prosa entfernen; Wikilinks aus der **bereinigten Prosa** (nicht aus dem Roh-Markdown) ziehen.
- [ ] Edge-Case-Verhalten festlegen und testen: (a) keine Fence, (b) mehrere Fences, (c) Fence ohne Sprach-Tag (kein Sidecar, aber aus Prosa entfernt), (d) Inline-Backticks in der Prosa.
- [ ] Sicherstellen, dass ein `[[wikilink]]` **innerhalb** eines Codeblocks NICHT als Link erscheint (folgt automatisch, da Wikilinks erst nach Fence-Entfernung extrahiert werden).
- [ ] `tests/test_content_parser.py` mit den unten genannten Fällen schreiben.
- [ ] Ruff über das neue Modul laufen lassen.

> Hinweis: zu entscheiden — Verhalten bei Alias-Wikilinks `[[ziel|anzeige]]`. Die Referenz-Regex liefert `ziel|anzeige` als Ganzes; ob der Anzeigeteil abgeschnitten werden soll, ist im Doc nicht spezifiziert.

## Akzeptanzkriterien

- [ ] Parser trennt Prosa und Code: der ` ```sql `-Block erscheint **nicht** in `ParsedNote.prose` (docs/05 §7: „Parser trennt Prosa/Code + extrahiert Links (CON-1)").
- [ ] `ParsedNote.sidecar_queries` enthält den SQL-Body (ohne die ` ``` `-Zäune), für `sql` und `cypher`.
- [ ] `ParsedNote.links` enthält die `[[wikilink]]`-Ziele aus der Prosa (z. B. `quadratic-formula`).
- [ ] Ein Wikilink, der nur in einem Codeblock steht, erscheint **nicht** in `links`.
- [ ] Notiz ohne Codeblock → `sidecar_queries == []`, Prosa unverändert (getrimmt).

## Tests / Verifikation

```bash
cd apps/api
uv run pytest ../../tests/test_content_parser.py -q
```

Erwartetes Ergebnis: alle Tests grün. Mindestens diese Assertions:

```python
from its.content.parser import parse_note

def test_code_is_separated_from_prose():
    md = "Text [[ziel]]\n\n```sql\nSELECT 1;\n```\n"
    p = parse_note(md)
    assert "SELECT 1" not in p.prose          # Code NICHT in Prosa (Embedding sauber)
    assert p.sidecar_queries == ["SELECT 1;"]  # Query als Sidecar
    assert p.links == ["ziel"]

def test_wikilink_in_code_is_ignored():
    md = "Prosa.\n\n```sql\n-- [[nicht_link]]\nSELECT 1;\n```\n"
    assert parse_note(md).links == []
```

## Abhängigkeiten

- **FND-2** (uv-Projekt / `pyproject.toml`): liefert die `uv`-Umgebung und `pytest`, gegen die der Parser entwickelt und getestet wird.
- **Nachgelagert:** **CON-2** importiert `parse_note`/`ParsedNote` direkt; **CON-3** liefert die Eingabedatei, an der der Parser real verifiziert wird.

## Definition of Done

- [ ] Akzeptanzkriterien aus docs/05 §7 (CON-1) erfüllt.
- [ ] Tests grün (`uv run pytest tests/test_content_parser.py`); Safety-Tests nicht betroffen (reine Funktion).
- [ ] Keine PII in externen LLM-Prompts — nicht betroffen (kein LLM-Call in diesem Task).
- [ ] `uv`-only, keine `pip`-Aufrufe.
- [ ] Zugehöriges GitHub-Issue (CON-1) geschlossen, E5-Epic-Checkliste aktualisiert.
