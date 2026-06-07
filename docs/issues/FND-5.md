## Ziel

Ein **Auth-Rollen-Gerüst** existiert: das `Role`-Enum (student/teacher/admin), die `Principal`-Datenklasse, die `current_principal`-FastAPI-Dependency (bewusst noch ein dokumentierter Stub) und das `PG_ROLE`-Mapping App-Rolle → Postgres-Rolle. Damit stehen genau die Rollen bereit, auf die die spätere RLS keyt.

## Kontext & Prinzipien

- **P1 (Safety in der DB):** Die hier definierten Postgres-Rollennamen (`its_student/its_teacher/its_admin`) sind **exakt** die, auf die die RLS-Policies in E3 (`docs/04`) keyen. Würde FND-5 andere Namen wählen, müsste E3 das Mapping brechen — deshalb wird es hier festgenagelt.
- **P5/P6 (Open Learner Model / Mensch im Loop):** Die Lehrer-Rolle ist ein erstklassiger Pfad (Verifizieren/Eingreifen), kein Admin-Nachgedanke — daher ist `teacher` eine eigene, gleichrangige Rolle im Enum, nicht ein Admin-Sonderfall.
- **P4 (PII):** `Principal` trägt `user_id`/`student_id` (Identifikatoren), aber **keine** Klartext-PII (kein Name/Geburtsdatum). Der spätere Agent erhält anonymisierten Kontext; das beginnt strukturell hier.
- **Sicherheits-Hinweis:** Der `current_principal`-Stub wirft bewusst `NotImplementedError` — es darf in M0 **kein** scheinbar funktionierender, aber unsicherer Auth-Pfad entstehen. Echtes JWT-Decoding ist ein expliziter TODO.

## Zu erstellende/ändernde Dateien

```
apps/api/src/its/auth/__init__.py     # Paketmarker
apps/api/src/its/auth/roles.py
apps/api/src/its/auth/deps.py
tests/test_auth_stub.py               # belegt 401 ohne Header + NotImplementedError mit Header
```

## Schnittstellen & Signaturen

`apps/api/src/its/auth/roles.py` (aus `docs/02` Section 5):

```python
from enum import StrEnum

class Role(StrEnum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"

# Mapping App-Rolle -> Postgres-Rolle (für RLS, docs/04)
PG_ROLE = {
    Role.STUDENT: "its_student",
    Role.TEACHER: "its_teacher",
    Role.ADMIN: "its_admin",
}
```

`apps/api/src/its/auth/deps.py` (aus `docs/02` Section 5):

```python
from dataclasses import dataclass
from fastapi import Depends, HTTPException, Header
from its.auth.roles import Role

@dataclass(frozen=True)
class Principal:
    user_id: str
    role: Role
    student_id: str | None = None   # gesetzt, wenn role == STUDENT

def current_principal(authorization: str | None = Header(default=None)) -> Principal:
    # TODO (FND-5): echtes JWT-Decoding gegen settings.jwt_public_key.
    # Vorerst Stub für lokale Entwicklung — MUSS vor Produktion ersetzt werden.
    if not authorization:
        raise HTTPException(status_code=401, detail="missing auth")
    raise NotImplementedError("JWT decoding to be implemented in FND-5")
```

> Kontext für die spätere RLS-Anbindung (aus `docs/04`): Die Postgres-Rollen `its_student/its_teacher/its_admin` werden in E3 angelegt; `scoped_session` setzt `app.current_student_id` (bzw. `app.current_teacher_id`) — das `PG_ROLE`-Mapping ist die Brücke dorthin.

## Umsetzungsschritte

- [ ] `apps/api/src/its/auth/__init__.py` (leer) anlegen.
- [ ] `roles.py` mit `Role`-StrEnum und `PG_ROLE`-Dict exakt wie oben anlegen.
- [ ] `deps.py` mit `Principal` (frozen dataclass) und `current_principal`-Stub anlegen.
- [ ] Sicherstellen, dass der Stub bei fehlendem Header `HTTPException(401)` wirft und bei vorhandenem Header `NotImplementedError` (klar markierter TODO).
- [ ] `tests/test_auth_stub.py` schreiben: (a) Import von `Role`, `PG_ROLE`, `Principal`, `current_principal`; (b) `current_principal(None)` → `HTTPException` mit `status_code == 401`; (c) `current_principal("Bearer x")` → `NotImplementedError`; (d) `PG_ROLE[Role.STUDENT] == "its_student"` etc.
- [ ] Keinen Router/Endpoint mit echter Auth mounten (nur Gerüst).

## Akzeptanzkriterien

- [ ] `Role`, `Principal`, `current_principal` und `PG_ROLE` sind vorhanden und importierbar.
- [ ] `PG_ROLE` mappt `STUDENT→its_student`, `TEACHER→its_teacher`, `ADMIN→its_admin` (exakt die RLS-Rollennamen aus `docs/04`).
- [ ] `current_principal` ist ein dokumentierter Stub mit klarer TODO-Markierung; ohne `Authorization` → `401`, mit → `NotImplementedError`.
- [ ] `Principal` enthält `user_id`, `role`, optionales `student_id`; keine Klartext-PII-Felder.
- [ ] `tests/test_auth_stub.py` ist grün.

## Tests / Verifikation

```bash
cd apps/api
uv run python -c "from its.auth.roles import Role, PG_ROLE; print(PG_ROLE[Role.STUDENT])"  # erwartet: its_student
uv run python -c "from its.auth.deps import Principal, current_principal; print('ok')"     # erwartet: ok
uv run pytest -q ../../tests/test_auth_stub.py   # erwartet: passed (401 + NotImplementedError belegt)
```

## Abhängigkeiten

- **Abhängig von:** FND-4 — das FastAPI-Skeleton/`its`-Paket muss existieren, damit `Header`/`HTTPException` aus FastAPI nutzbar sind und die App das Auth-Modul später einbinden kann.
- **Nachgelagert:** E3/Safety (`docs/04`) — RLS-Policies und `scoped_session` keyen auf den hier definierten `PG_ROLE`-Namen; spätere API-Tasks nutzen `current_principal` als Dependency (sobald echtes JWT-Decoding implementiert ist).

## Definition of Done

- [ ] Akzeptanzkriterien dieses Tasks erfüllt.
- [ ] Tests grün (`tests/test_auth_stub.py`).
- [ ] Keine Klartext-PII in `Principal`; Stub erlaubt keinen unsicheren Auth-Bypass (wirft, statt einen Fake-Principal zu liefern).
- [ ] `uv`-only (alle Läufe via `uv run`, kein `pip`).
- [ ] GitHub-Issue FND-5 geschlossen, E1-Epic-Checkliste aktualisiert.
