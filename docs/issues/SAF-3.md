## Ziel

Eine zentrale Min-Cohort-Schwelle verweigert Aggregate, deren Gruppe kleiner als `k` ist (Default `k=10` aus `settings`). Jede Population-Query muss durch diese eine Stelle laufen, bevor ein Resultat das System verlaesst — so wird der Aggregat-Leak (de-anonymisierte Einzelauskunft) fail-closed verhindert.

## Kontext & Prinzipien

- **P1 (Safety zuerst):** Die Schwelle ist fail-closed (`n < k` → Verweigerung) und die *einzige* Stelle, durch die Aggregate gehen. Eine zentrale Schranke ist auditierbar und kann nicht versehentlich an einzelnen Call-Sites "vergessen" werden, wenn die Konvention eingehalten wird.
- **P8 (Datenresidenz / Schutz Minderjaehriger):** Min-Cohort ist die Gegenmassnahme gegen De-Anonymisierung ueber Aggregate — eine zentrale DSG/DSGVO-relevante Schutzmassnahme fuer Kinderdaten.
- **P5 (Open Learner Model):** Population-Aggregate (z. B. Klassen-Mastery) sind fuer die Lehrperson gedacht; die Schwelle stellt sicher, dass diese Sicht keine Einzelperson entlarvt, auch wenn ein Filter zufaellig nur eine Person trifft.

## Zu erstellende/aendernde Dateien

- `apps/api/src/its/safety/cohort.py` — neue Schwellen-Durchsetzung. Liegt im `safety/`-Modul gemaess Repo-Layout (Section 6: `safety/ # rls.sql, cohort.py, scoping.py`).

Konsumiert (nicht zu aendern):
- `apps/api/src/its/config.py` (`settings.min_cohort_k`, Default 10).

## Schnittstellen & Signaturen

`apps/api/src/its/safety/cohort.py` (Referenz aus docs/04 §4):

```python
from dataclasses import dataclass
from its.config import settings

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

Konfiguration (aus docs/02 §4 / `config.py`):

```python
class Settings(BaseSettings):
    ...
    min_cohort_k: int = 10
settings = Settings()  # type: ignore[call-arg]
```

Nachgelagerter Konsument (docs/05 §4, RET-4) — zeigt die erwartete Nutzung:

```python
from its.safety.cohort import enforce_min_cohort

def skill_mastery_distribution(session, class_id, skill_id):
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

## Umsetzungsschritte

- [ ] `apps/api/src/its/safety/cohort.py` anlegen mit `CohortTooSmall(PermissionError)`.
- [ ] `CohortResult` als `@dataclass(frozen=True)` mit Feldern `n: int` und `payload: dict`.
- [ ] `enforce_min_cohort(n, payload, k=None)` exakt wie spezifiziert: `threshold = k if k is not None else settings.min_cohort_k`; bei `n < threshold` → `CohortTooSmall`; sonst `CohortResult(n=n, payload=payload)`.
- [ ] Strikt `<` verwenden (nicht `<=`): `n == k` ist erlaubt, `n < k` wird verweigert.
- [ ] Sicherstellen, dass `CohortTooSmall` von `PermissionError` erbt (fuer das API-403-Mapping in API-3).
- [ ] Keine zusaetzliche Logik (kein DB-Zugriff, kein Logging-Zwang) — reine Funktion; die Query-Erzeugung gehoert nach RET-4.

> Hinweis: zu entscheiden — ob `k` zukuenftig pro Klasse/Fach uebersteuerbar sein soll. Aktuell global ueber `settings.min_cohort_k`; der optionale `k`-Parameter erlaubt Call-Site-Overrides und bleibt erhalten.

## Akzeptanzkriterien

- [ ] Aggregate mit `n < k` werfen `CohortTooSmall`.
- [ ] Default `k=10` wird aus `settings.min_cohort_k` bezogen, wenn kein `k` uebergeben wird.
- [ ] Es gibt **eine** zentrale Stelle (`enforce_min_cohort`), durch die jede Aggregat-Antwort geht.
- [ ] Grenzfall: `n == k` ist erlaubt (Payload wird durchgereicht).
- [ ] `CohortTooSmall` ist Subklasse von `PermissionError`.

## Tests / Verifikation

```bash
cd apps/api && uv run pytest tests/test_cohort_threshold.py -q
```

Verbindliche Mindestfaelle (aus docs/04 §5):

```python
import pytest
from its.safety.cohort import enforce_min_cohort, CohortTooSmall

def test_small_cohort_refused():
    with pytest.raises(CohortTooSmall):
        enforce_min_cohort(n=3, payload={"avg": 0.7}, k=10)

def test_sufficient_cohort_ok():
    res = enforce_min_cohort(n=25, payload={"avg": 0.7}, k=10)
    assert res.n == 25 and res.payload["avg"] == 0.7
```

Empfohlene Ergaenzung (Grenzwert + Default):

```python
def test_boundary_n_equals_k_allowed():
    assert enforce_min_cohort(n=10, payload={}, k=10).n == 10

def test_default_k_from_settings():
    # ohne k -> settings.min_cohort_k (Default 10): n=9 wird verweigert
    with pytest.raises(CohortTooSmall):
        enforce_min_cohort(n=9, payload={})
```

Erwartetes Ergebnis: alle Tests gruen; `test_cohort_threshold.py` ist Teil des CI-blockierenden Safety-Gates (SAF-4).

## Abhaengigkeiten

- **DB-3** — stellt das Datenmodell/`scoped_session` bereit, in dessen Kontext Aggregate (RET-4) entstehen; `enforce_min_cohort` selbst ist DB-frei, gehoert aber in die Safety-Schicht von M1.
- Konsumiert **FND-2/FND-4** (`config.py`/`settings`) fuer den Default-`k`.
- Nachgelagert warten: **RET-4** (`population.py` ruft `enforce_min_cohort` ausschliesslich), **API-2** (`/teacher/class/{id}/skill/{id}/distribution` via Min-Cohort), **API-3** (Exception-Handler mappt `CohortTooSmall` → 403 neutral), **SAF-4** (beweist die Schwelle).

## Definition of Done

- [ ] Akzeptanzkriterien aus docs/04 §4 erfuellt.
- [ ] Tests gruen, inkl. `tests/test_cohort_threshold.py` (Teil des Safety-Gates).
- [ ] Kein PII in externen LLM-Prompts (nicht betroffen).
- [ ] `uv`-only, keine `pip`-Aufrufe.
- [ ] Zugehoeriges GitHub-Issue SAF-3 geschlossen, E3-Epic-Checkliste aktualisiert.
