## Ziel

Eine Funktion `skill_mastery_distribution(session, class_id, skill_id)` berechnet ein Klassen-Aggregat (Anzahl + durchschnittliche Mastery) und gibt es **ausschliesslich** durch `enforce_min_cohort` (SAF-3) zurueck — Aggregate ueber zu kleine Gruppen werden verweigert, um eine De-Anonymisierung Einzelner zu verhindern.

## Kontext & Prinzipien

- **P1 (Safety zuerst) — `safety-critical`:** Der **Aggregat-Leak** (eine "Population"-Query, die genau eine Person trifft, wird zur Einzelauskunft) wird durch die **Min-Cohort-Schwelle** geschlossen — fail-closed. Es gibt **keinen** Codepfad, der ein rohes Aggregat zurueckgibt.
- **P6 (Mensch im Loop ist Sicherheitsarchitektur):** Die Schwelle ist eine harte Garantie, kein Reporting-Detail; sie laeuft durch **eine** zentrale Stelle (`enforce_min_cohort`).
- **P7:** Eine Implementierung, flaches Modul `retrieval/`.
- **P8 (CH/EU-Residenz):** Aggregate werden in der CH/EU-DB berechnet und verlassen das System nur in aggregierter, schwellengepruefter Form.
- **P9 (`uv`-only).**

## Zu erstellende/aendernde Dateien

- `apps/api/src/its/retrieval/population.py` (neu) — Kernimplementierung.
- `tests/test_population.py` (neu) — Test der Schwellen-Durchsetzung.

## Schnittstellen & Signaturen

Referenz aus `docs/05-retrieval.md`, Abschnitt 4 — exakt zu reproduzieren:

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

Abhaengige Schnittstelle (aus `docs/04-safety.md`, SAF-3) — Verhalten, auf das sich RET-4 verlaesst:

```python
class CohortTooSmall(PermissionError):
    pass

@dataclass(frozen=True)
class CohortResult:
    n: int
    payload: dict

def enforce_min_cohort(n: int, payload: dict, k: int | None = None) -> CohortResult:
    """Verweigert Aggregate, deren Gruppe kleiner als k ist (Default aus settings.min_cohort_k).
    JEDE Population-Query MUSS hierdurch laufen, bevor ein Resultat das System verlaesst."""
    threshold = k if k is not None else settings.min_cohort_k
    if n < threshold:
        raise CohortTooSmall(f"cohort n={n} below threshold k={threshold}")
    return CohortResult(n=n, payload=payload)
```

Relevantes Schema (aus `docs/03-database.md`):

```sql
CREATE TABLE enrollments (
  student_id uuid REFERENCES students(id) ON DELETE CASCADE,
  class_id   uuid REFERENCES classes(id)  ON DELETE CASCADE,
  PRIMARY KEY (student_id, class_id)
);
-- learner_state: (student_id, skill_id, mastery, uncertainty, attempts_count)
```

Default-Schwelle: `settings.min_cohort_k` (Default `k=10`, aus `docs/02`/`docs/04`).

## Umsetzungsschritte

- [ ] `skill_mastery_distribution` exakt wie oben implementieren; `count(*)` und `avg(mastery)` in **einer** Query, gefiltert nach `class_id` und `skill_id`.
- [ ] `class_id`/`skill_id` per Bindparam (kein String-Format).
- [ ] Ergebnis **immer** durch `enforce_min_cohort` schleusen — kein direkter Return des rohen Aggregats.
- [ ] `avg_mastery` auf 3 Nachkommastellen runden; `None` (leere Kohorte) zu `0.0` defaulten (`row.avg_mastery or 0.0`).
- [ ] `n` als `int` casten.
- [ ] `CohortTooSmall` **nicht** im Modul abfangen — die Verweigerung soll bis zum Aufrufer (Agent/API) durchschlagen.
- [ ] `ruff`-clean.

## Akzeptanzkriterien

- [ ] Das Aggregat verlaesst die Funktion **ausschliesslich** ueber `enforce_min_cohort`.
- [ ] Kohorte mit `n < k` → `CohortTooSmall` (Default `k=10` aus `settings`).
- [ ] Kohorte mit `n >= k` → `CohortResult` mit `payload={"avg_mastery": <gerundet>}`.
- [ ] Leere Kohorte fuehrt nicht zu einem Crash (avg=None → 0.0), wird aber durch die Schwelle verweigert (n=0 < k).

## Tests / Verifikation

```bash
cd apps/api
uv run pytest ../../tests/test_population.py -q
```

Testaufbau (Integration, Test-DB; Fixtures aus `docs/10`):
- Klasse mit < k Schuelern (z. B. 3) + `learner_state` seeden → `skill_mastery_distribution` wirft `CohortTooSmall` (pytest.raises).
- Klasse mit >= k Schuelern (z. B. 12) seeden → liefert `CohortResult` mit `payload["avg_mastery"]` im Bereich [0,1].
- Reiner Schwellen-Unit-Test (aus `docs/04`/`docs/10`): `enforce_min_cohort(n=3, payload={...}, k=10)` → `CohortTooSmall`; `n=25` → Payload durch.

## Abhaengigkeiten

- **SAF-3** (`enforce_min_cohort`, `CohortTooSmall`, `CohortResult`): die zentrale Schwellen-Durchsetzung, ohne die RET-4 nicht definiert ist.
- **(implizit) DB-2** (`learner_state`, `enrollments`): die aggregierten Tabellen.
- **Nachgelagert:** AG-2 (`agent/nodes/retrieve.py`) im POPULATION-Pfad; E9 (`api/teacher.py`) als Klassen-/Dashboard-Endpunkt.

> Hinweis: zu entscheiden — der Plan erwaehnt "Soft-Kohorten via Vektor-Aehnlichkeit (Lernende wie diese:r)"; deren Definition ist offen. Fuer dieses Epic bleibt die Kohorte die harte `class_id`-Gruppe; das Aggregat laeuft in beiden Faellen durch dieselbe Schwelle.

## Definition of Done

- [ ] Akzeptanzkriterien erfuellt.
- [ ] `tests/test_population.py` gruen, inkl. der Verweigerung kleiner Kohorten (Safety-Eigenschaft).
- [ ] Kein externer LLM-Call → keine PII-Pruefung noetig.
- [ ] `uv`-only, keine `pip`-Aufrufe.
- [ ] GitHub-Issue RET-4 geschlossen, E4-Checkliste aktualisiert.
