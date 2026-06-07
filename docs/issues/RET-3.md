## Ziel

Eine RLS-geschuetzte Funktion `mastery_overview(session, principal)` liefert den Mastery-Stand (inkl. Unsicherheit und Versuchszahl) genau **eines** Schuelers — die `student_id` wird zwingend ueber `require_student_scope` aufgeloest, sodass es keinen ungescopten Codepfad gibt.

## Kontext & Prinzipien

- **P1 (Safety zuerst, in der DB) — `safety-critical`:** Die Isolation wird durch **Postgres Row-Level Security** erzwungen, nicht durch `if`-Checks. RET-3 nutzt zusaetzlich `require_student_scope` (App-Schicht, fail-closed). **Doppelte Absicherung:** Selbst wenn der Code den Filter vergaesse, verweigert RLS fremde Zeilen.
- **P5 (Open Learner Model):** Die Rueckgabe enthaelt `uncertainty` — der Lernstand ist inkl. seiner Unsicherheit fuer Menschen inspizierbar (interpretierbares BKT, keine Black-Box).
- **P4 (PII bleibt in der DB):** Die Funktion gibt `display_name`/IDs nur innerhalb des Systems zurueck; an ein externes LLM gelangt nichts davon (das ist Sache des Agenten/`anonymize`).
- **P7:** Eine Implementierung, flaches Modul `retrieval/`.
- **P9 (`uv`-only).**

## Zu erstellende/aendernde Dateien

- `apps/api/src/its/retrieval/individual.py` (neu) — Kernimplementierung.
- `tests/test_individual.py` (neu) — Integrationstest gegen RLS-aktivierte Test-DB.

## Schnittstellen & Signaturen

Referenz aus `docs/05-retrieval.md`, Abschnitt 3 — exakt zu reproduzieren:

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

Abhaengige Schnittstelle (aus `docs/04-safety.md`, SAF-2) — Verhalten, auf das sich RET-3 verlaesst:

```python
class ScopeError(PermissionError):
    pass

def require_student_scope(principal: Principal) -> str:
    """Gibt die student_id zurueck, auf die eine Individual-Query zwingend gescoped wird.
    Fail-closed: kein Scope -> ScopeError, niemals 'alle'."""
    if principal.role == Role.STUDENT:
        if not principal.student_id:
            raise ScopeError("student without student_id")
        return principal.student_id
    raise ScopeError("individual query requires a student-scoped principal")
```

Principal (aus `docs/02-foundations.md`, FND-5):

```python
@dataclass(frozen=True)
class Principal:
    user_id: str
    role: Role
    student_id: str | None = None   # gesetzt, wenn role == STUDENT
```

Relevantes Schema (`learner_state`, aus `docs/03-database.md`):

```sql
CREATE TABLE learner_state (
  student_id     uuid NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  skill_id       uuid NOT NULL REFERENCES skills(id),
  mastery        double precision NOT NULL DEFAULT 0.0,  -- P(known)
  uncertainty    double precision NOT NULL DEFAULT 1.0,  -- fuer Open Learner Model (P5)
  attempts_count int NOT NULL DEFAULT 0,
  updated_at     timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (student_id, skill_id)
);
```

## Umsetzungsschritte

- [ ] `mastery_overview` exakt wie oben implementieren; `require_student_scope(principal)` **zuerst** aufrufen (fail-closed).
- [ ] `sid` per Bindparam in die Query geben (kein String-Format).
- [ ] Defense-in-depth: Code-Filter `WHERE ls.student_id = :sid` **und** die uebergebene Session ist RLS-gescoped (`scoped_session`/`db_factory.as_student`).
- [ ] Rueckgabe `list[dict]` mit `skill_id`, `name`, `mastery`, `uncertainty`, `attempts_count`, sortiert nach `s.name`.
- [ ] Keine zusaetzliche Anonymisierung im Modul (PII verlaesst die DB hier nicht).
- [ ] `ruff`-clean.

## Akzeptanzkriterien

- [ ] Es existiert **kein** Codepfad, der die Query ohne aufgeloesten Scope ausfuehrt; fehlender Scope wirft `ScopeError`.
- [ ] Die Rueckgabe enthaelt `mastery` **und** `uncertainty` (P5).
- [ ] Doppelte Absicherung: Code-Filter `student_id = :sid` plus RLS-Session.
- [ ] Ein Schueler erhaelt ausschliesslich eigene Zeilen — auch wenn der Code-Filter (hypothetisch) fehlte, liefert RLS fremde Zeilen nicht.

## Tests / Verifikation

```bash
cd apps/api
uv run pytest ../../tests/test_individual.py -q
```

Testaufbau (Integration, RLS-aktivierte Test-DB; `db_factory`/`two_students` aus `docs/10` `conftest.py`):
- Zwei Schueler A, B mit je `learner_state`-Zeilen seeden.
- `mastery_overview` als Schueler A (Principal mit `role=STUDENT`, `student_id=A`, Session via `db_factory.as_student(A)`) → liefert **nur** A-Zeilen, **0** B-Zeilen.
- Principal ohne `student_id` bzw. mit `role=TEACHER` → `ScopeError` (pytest.raises).
- Gegenprobe: A sieht die eigenen Zeilen (> 0).

## Abhaengigkeiten

- **SAF-2** (`require_student_scope`, `ScopeError`): liefert die fail-closed Scope-Aufloesung, ohne die RET-3 nicht definiert ist.
- **(implizit) SAF-1/DB-3** (RLS-Policies + `scoped_session`): liefern die zweite Absicherungsschicht; RET-3 erwartet eine RLS-gescopte Session.
- **(implizit) DB-2** (`learner_state`, `skills`): die abgefragten Tabellen/Modelle.
- **Nachgelagert:** AG-2 (`agent/nodes/retrieve.py`) im INDIVIDUAL-Pfad; E9 (`api/student.py`) als Endpunkt.

> Hinweis: zu entscheiden — der Lehrer-Zugriff auf den Stand eines Schuelers laeuft laut RLS ueber `app.current_teacher_id`; `require_student_scope` deckt jedoch nur den Schueler-Principal ab. Ob RET-3 auch einen Lehrer-Pfad (`teacher_id_of`) erhaelt oder ob das ein separater Endpunkt in E9 wird, ist offen.

## Definition of Done

- [ ] Akzeptanzkriterien erfuellt.
- [ ] `tests/test_individual.py` gruen, inkl. der Safety-Eigenschaft (A sieht keine B-Zeilen), gegen echtes Postgres mit RLS.
- [ ] Kein externer LLM-Call → PII verlaesst die Maschine nicht.
- [ ] `uv`-only, keine `pip`-Aufrufe.
- [ ] GitHub-Issue RET-3 geschlossen, E4-Checkliste aktualisiert.
