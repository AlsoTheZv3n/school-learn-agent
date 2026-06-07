## Ziel

Ein anwendungsseitiger Scoping-Resolver stellt sicher, dass keine Individual-Query ohne aufgeloesten Schueler-Scope ausgefuehrt werden kann. Fehlt der Scope, wird `ScopeError` geworfen — niemals stillschweigend "alle" zurueckgegeben. Der Resolver ist die zweite, der RLS vorgelagerte Schranke gegen den Individual-Leak.

## Kontext & Prinzipien

- **P1 (Safety zuerst, in der DB verankert):** RLS ist die *primaere* Schranke; SAF-2 ist eine bewusst redundante, anwendungsseitige Schranke. Defense-in-depth: Selbst wenn eine RLS-Variable im Code falsch gesetzt wuerde, verlangt SAF-2 einen expliziten Scope, bevor eine Individual-Query ueberhaupt formuliert wird.
- **P6 (Mensch im Loop als Sicherheitsarchitektur):** `teacher_id_of` trennt Lehrer- von Schueler-Pfaden sauber, sodass die Lehreraufsicht ein erstklassiger, klar abgegrenzter Pfad bleibt — keine Vermischung von Identitaeten.
- **P4 (PII verlaesst die Maschine nicht im Klartext):** Der Resolver arbeitet ausschliesslich mit IDs (`student_id`, `user_id`), nie mit Klartext-Profilen — passend zur Anonymisierungs-Disziplin downstream.

## Zu erstellende/aendernde Dateien

- `apps/api/src/its/safety/scoping.py` — neuer Resolver. Liegt im `safety/`-Modul gemaess Repo-Layout (Section 6: `safety/ # rls.sql, cohort.py, scoping.py`).

Konsumiert (nicht zu aendern):
- `apps/api/src/its/auth/deps.py` (`Principal`)
- `apps/api/src/its/auth/roles.py` (`Role`)

## Schnittstellen & Signaturen

`apps/api/src/its/safety/scoping.py` (Referenz aus docs/04 §3):

```python
from its.auth.deps import Principal
from its.auth.roles import Role

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

def teacher_id_of(principal: Principal) -> str:
    if principal.role != Role.TEACHER:
        raise ScopeError("not a teacher principal")
    return principal.user_id
```

Kontext der konsumierten Typen (aus docs/02 §5 / docs/03):

```python
# its/auth/roles.py
class Role(StrEnum):
    STUDENT = "student"; TEACHER = "teacher"; ADMIN = "admin"

# its/auth/deps.py
@dataclass(frozen=True)
class Principal:
    user_id: str
    role: Role
    student_id: str | None = None   # gesetzt, wenn role == STUDENT
```

Nachgelagerter Konsument (docs/05 §3, RET-3) — zeigt die erwartete Nutzung:

```text
Individual-Query immer auf einen student_id gescoped — ueber require_student_scope (SAF-2)
und zusaetzlich RLS. Niemals ohne Scope ausfuehrbar.
```

## Umsetzungsschritte

- [ ] `apps/api/src/its/safety/scoping.py` mit `ScopeError(PermissionError)` anlegen.
- [ ] `require_student_scope(principal)` exakt wie spezifiziert implementieren: Student mit `student_id` → ID; Student ohne `student_id` → `ScopeError`; jede andere Rolle → `ScopeError`.
- [ ] `teacher_id_of(principal)` implementieren: nur fuer `Role.TEACHER`, sonst `ScopeError`; gibt `principal.user_id` zurueck.
- [ ] Keine zusaetzliche Logik erfinden (keine DB-Zugriffe, kein Logging-Zwang) — der Resolver ist eine reine Funktion ueber dem `Principal`.
- [ ] Sicherstellen, dass `ScopeError` von `PermissionError` erbt (damit der zentrale API-Exception-Handler in API-3 ihn auf 403 mappen kann).
- [ ] Optionale, empfohlene Unit-Tests anlegen (formal Teil von TST, aber hier sinnvoll als Selbst-Verifikation).

> Hinweis: zu entscheiden — `teacher_id_of` liefert `principal.user_id`, waehrend die RLS-Variable `app.current_teacher_id` heisst und laut docs/03 von `scoped_session` gesetzt wird. Die Konvention "`scoped_session` setzt die Variable, der Resolver liefert nur den Wert" sollte dokumentiert werden, um Doppel-Setzen zu vermeiden.

## Akzeptanzkriterien

- [ ] Es gibt keinen Codepfad, der eine Individual-Query *ohne* aufgeloesten Scope ausfuehrt; fehlender Scope wirft `ScopeError`.
- [ ] `require_student_scope` gibt fuer einen Student-Principal mit `student_id` genau diese ID zurueck.
- [ ] `require_student_scope` wirft `ScopeError` fuer (a) Student ohne `student_id`, (b) jede Nicht-Student-Rolle.
- [ ] `teacher_id_of` gibt fuer Lehrer `user_id` zurueck und wirft sonst `ScopeError`.
- [ ] `ScopeError` ist eine Subklasse von `PermissionError`.

## Tests / Verifikation

```bash
cd apps/api && uv run pytest tests/test_scoping.py -q
```

Empfohlene Mindest-Assertions (falls `tests/test_scoping.py` angelegt wird):

```python
import pytest
from its.auth.deps import Principal
from its.auth.roles import Role
from its.safety.scoping import require_student_scope, teacher_id_of, ScopeError

def test_student_scope_resolved():
    p = Principal(user_id="u1", role=Role.STUDENT, student_id="s1")
    assert require_student_scope(p) == "s1"

def test_student_without_id_fails_closed():
    p = Principal(user_id="u1", role=Role.STUDENT, student_id=None)
    with pytest.raises(ScopeError):
        require_student_scope(p)

def test_teacher_cannot_run_individual_scope():
    p = Principal(user_id="t1", role=Role.TEACHER)
    with pytest.raises(ScopeError):
        require_student_scope(p)
    assert teacher_id_of(p) == "t1"
```

Erwartetes Ergebnis: alle Tests gruen; kein Fall, in dem `require_student_scope` ohne aufgeloesten Scope zurueckkehrt.

## Abhaengigkeiten

- **SAF-1** — die RLS-Schranke; SAF-2 ist die ergaenzende anwendungsseitige Schranke (defense-in-depth), nicht ihr Ersatz.
- **FND-5** — liefert `Role`, `Principal`, auf denen der Resolver operiert; ohne sie ist die Signatur nicht erfuellbar.
- Nachgelagert warten: **RET-3** (`individual.py` nutzt `require_student_scope`), **API-1** (Student-Endpunkte scopen via SAF-2), **API-3** (Exception-Handler mappt `ScopeError` → 403 neutral).

## Definition of Done

- [ ] Akzeptanzkriterien aus docs/04 §3 erfuellt.
- [ ] Tests gruen (Scoping-Unit-Tests; sowie die Safety-Suite, sobald SAF-4 vorliegt).
- [ ] Kein PII in externen LLM-Prompts (nicht betroffen; reiner ID-Resolver).
- [ ] `uv`-only, keine `pip`-Aufrufe.
- [ ] Zugehoeriges GitHub-Issue SAF-2 geschlossen, E3-Epic-Checkliste aktualisiert.
