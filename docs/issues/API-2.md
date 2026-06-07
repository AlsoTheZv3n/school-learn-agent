## Ziel

Die Lehrer-HTTP-Endpoints: das Open Learner Model eines Schülers lesen (inkl. `uncertainty`), die Mastery-Verteilung einer Klasse für einen Skill über die Min-Cohort-Schwelle abrufen und Lehrer-Notizen/Mastery-Overrides schreiben. Am Ende sieht eine Lehrperson ausschliesslich Schüler:innen der eigenen Klassen (RLS-erzwungen), Kohorten-Aggregate kleiner Gruppen werden verweigert, und Interventionen sind persistierbar.

## Kontext & Prinzipien

- **P1 (Safety zuerst, in der DB):** Die RLS-Policies `teacher_state_in_class`/`teacher_attempts_in_class` stellen über `app.current_teacher_id` sicher, dass nur Zeilen von Schüler:innen in den eigenen Klassen sichtbar sind — **nicht** durch Query-Disziplin, sondern durch das Schema. `scoped_session` setzt die PG-Rolle `its_teacher` + die Lehrer-Session-Variable.
- **P5 (Open Learner Model):** `GET /teacher/student/{id}/mastery` liefert die **vollständige** Sicht inkl. `uncertainty` — die Lehrperson sieht, *wie sicher* die Einschätzung ist, nicht nur eine Zahl. Das ist der bewusste Gegenpol zur schonenden Schülersicht (API-1).
- **P6 (Mensch im Loop ist Sicherheitsarchitektur):** `POST /teacher/student/{id}/note` (Notiz + optionaler `override_mastery`) ist ein erstklassiger Pfad, kein Admin-Nachgedanke. Eine KI ist nicht alleinige Instanz über den Lernweg.
- **P3 (Aggregat-Schutz / Min-Cohort):** Die Klassenverteilung läuft ausschliesslich durch `enforce_min_cohort` (SAF-3) — ein Aggregat über eine Gruppe `n<k` würde zur de-anonymisierten Einzelauskunft.

## Zu erstellende/ändernde Dateien

- `apps/api/src/its/api/teacher.py` (neu) — Router mit den drei Lehrer-Endpoints.
- `apps/api/src/its/main.py` (ändern) — `app.include_router(teacher_router)`.

## Schnittstellen & Signaturen

Referenz-Implementierung aus `docs/08-backend-api.md` §3:

```python
from fastapi import APIRouter, Depends
from sqlalchemy import text   # im Doc-Snippet fehlend, hier ergänzt
from its.auth.deps import Principal, current_principal
from its.db.session import scoped_session
from its.api.schemas import SkillMastery, CohortStat

router = APIRouter(prefix="/teacher", tags=["teacher"])

@router.get("/student/{student_id}/mastery", response_model=list[SkillMastery])
def student_mastery(student_id: str, principal: Principal = Depends(current_principal)):
    # RLS (teacher_*_in_class) stellt sicher: nur Schüler:innen der eigenen Klassen sichtbar.
    with scoped_session(principal) as s:
        rows = s.execute(text("""
          SELECT ls.skill_id::text, sk.name, ls.mastery, ls.uncertainty, ls.attempts_count
          FROM learner_state ls JOIN skills sk ON sk.id = ls.skill_id
          WHERE ls.student_id = :sid
        """).bindparams(sid=student_id)).mappings().all()
    return [SkillMastery(**r) for r in rows]   # inkl. uncertainty (Open Learner Model)

@router.get("/class/{class_id}/skill/{skill_id}/distribution", response_model=CohortStat)
def class_distribution(class_id: str, skill_id: str,
                       principal: Principal = Depends(current_principal)):
    from its.retrieval.population import skill_mastery_distribution
    with scoped_session(principal) as s:
        res = skill_mastery_distribution(s, class_id, skill_id)   # via enforce_min_cohort
    return CohortStat(n=res.n, avg_mastery=res.payload["avg_mastery"])

@router.post("/student/{student_id}/note")
def add_note(student_id: str, body: str, skill_id: str | None = None,
             override_mastery: float | None = None,
             principal: Principal = Depends(current_principal)):
    # Lehrer-Intervention (P6): Notiz + optionaler Mastery-Override.
    with scoped_session(principal) as s:
        s.execute(text("""
          INSERT INTO teacher_notes (student_id, teacher_id, skill_id, body, override_mastery)
          VALUES (:sid, :tid, :skid, :b, :ov)
        """).bindparams(sid=student_id, tid=principal.user_id, skid=skill_id,
                        b=body, ov=override_mastery))
    return {"status": "ok"}
```

> Korrekturen/Hinweise zum Doc-Auszug:
> - `from sqlalchemy import text` fehlt im Snippet — ergänzt (sonst NameError).
> - `add_note` nimmt `body`/`skill_id`/`override_mastery` als **Query-Parameter**. Empfehlung: ein Pydantic-`NoteIn`-Body, damit Freitext über Minderjährige (PII) nicht in der URL und damit in Server-Logs landet (P4). > Hinweis: zu entscheiden — Schema-Form (offene Frage des Epics).

Genutzte Bausteine (Referenz):

```python
# its.retrieval.population (RET-4) — Aggregat NUR via enforce_min_cohort
def skill_mastery_distribution(session, class_id: str, skill_id: str):
    row = session.execute(text("""
        SELECT count(*) AS n, avg(ls.mastery) AS avg_mastery
        FROM learner_state ls JOIN enrollments e ON e.student_id = ls.student_id
        WHERE e.class_id = :cid AND ls.skill_id = :skid
    """).bindparams(cid=class_id, skid=skill_id)).one()
    return enforce_min_cohort(n=int(row.n),
        payload={"avg_mastery": round(float(row.avg_mastery or 0.0), 3)})

# its.safety.cohort (SAF-3)
class CohortTooSmall(PermissionError): ...
@dataclass(frozen=True)
class CohortResult: n: int; payload: dict
def enforce_min_cohort(n: int, payload: dict, k: int | None = None) -> CohortResult: ...
```

Relevante RLS-Policies (Referenz, aus docs/04 §2 — müssen live sein, SAF-1):

```sql
CREATE POLICY teacher_state_in_class ON learner_state
  FOR SELECT TO its_teacher
  USING (student_id IN (
    SELECT e.student_id FROM enrollments e JOIN classes c ON c.id = e.class_id
    WHERE c.teacher_id = NULLIF(current_setting('app.current_teacher_id', true), '')::uuid));

CREATE POLICY teacher_notes_rw ON teacher_notes
  FOR ALL TO its_teacher
  USING (teacher_id = NULLIF(current_setting('app.current_teacher_id', true), '')::uuid)
  WITH CHECK (teacher_id = NULLIF(current_setting('app.current_teacher_id', true), '')::uuid);
```

> `scoped_session` muss für Lehrer zusätzlich `SET app.current_teacher_id` setzen (docs/04 §2 Ergänzung an DB-3). Diese Endpoints setzen das voraus.

## Umsetzungsschritte

- [ ] `teacher.py` anlegen: `APIRouter(prefix="/teacher", tags=["teacher"])`, `from sqlalchemy import text` importieren.
- [ ] `GET /student/{student_id}/mastery`: Roh-Query (inkl. `ls.skill_id::text`, `uncertainty`) in `scoped_session`; `.mappings().all()` → `list[SkillMastery]`.
- [ ] Sicherstellen, dass `student_id` (Path-`str`) als UUID gegen `ls.student_id` bindet (Postgres castet `text`→`uuid` beim Vergleich; bei Bedarf explizit `:sid::uuid`).
  > Hinweis: zu entscheiden — Pydantic-`UUID` im Pfad vs. `str` (offene Frage des Epics).
- [ ] `GET /class/{class_id}/skill/{skill_id}/distribution`: `skill_mastery_distribution(s, class_id, skill_id)` aufrufen; `CohortStat(n=res.n, avg_mastery=res.payload["avg_mastery"])`.
- [ ] Verifizieren, dass `CohortTooSmall` **nicht** lokal abgefangen wird, sondern bis zum zentralen Handler (API-3) propagiert → `403` neutral.
- [ ] `POST /student/{student_id}/note`: Insert in `teacher_notes` (`student_id`, `teacher_id=principal.user_id`, `skill_id`, `body`, `override_mastery`).
- [ ] `body` (und optional `skill_id`/`override_mastery`) als Pydantic-Body-Schema modellieren statt Query-Param (PII nicht in der URL).
- [ ] `override_mastery` auf gültigen Bereich validieren (z. B. `0.0 <= x <= 1.0`).
- [ ] In `main.py`: `from its.api.teacher import router as teacher_router; app.include_router(teacher_router)`.

## Akzeptanzkriterien

- [ ] `GET /teacher/student/{id}/mastery` liefert die Skill-Mastery **inkl. `uncertainty`** (Open Learner Model).
- [ ] Lehrer sehen nur Schüler:innen ihrer eigenen Klassen — durch RLS erzwungen, nicht durch Query-Disziplin. Ein Fremdschüler liefert eine **leere** Liste (RLS filtert die Zeilen weg), keinen Datenleak.
- [ ] `GET /teacher/class/{id}/skill/{id}/distribution` läuft ausschliesslich über `enforce_min_cohort`; eine kleine Kohorte (`n<k`) → `403` neutral.
- [ ] `POST /teacher/student/{id}/note` schreibt Notiz und optionalen `override_mastery` in `teacher_notes`; Antwort `{"status":"ok"}` (bzw. `200`).
- [ ] Alle drei Endpoints laufen in `scoped_session` mit Rolle `its_teacher`.

## Tests / Verifikation

Voraussetzung: Docker-DB mit angewandtem `rls.sql`; Seed mit Lehrer, Klasse, Enrollments, `learner_state`. Auth via `app.dependency_overrides[current_principal]` (Lehrer-`Principal`).

- [ ] `tests/test_api_teacher.py` (FastAPI-`TestClient`):
  - Lehrer T1 (Klasse mit Schüler A) → `GET /teacher/student/{A}/mastery` liefert As Skills inkl. `uncertainty`.
  - T1 → `GET /teacher/student/{X}/mastery` für einen **fremden** Schüler X (andere Klasse) → **leere** Liste (RLS).
  - `GET /teacher/class/{C}/skill/{S}/distribution` mit kleiner Kohorte (`n<10`) → `403`, Body neutral (kein `n=`).
  - Mit ausreichender Kohorte (`n>=10`) → `200`, `CohortStat` mit `n` und `avg_mastery`.
  - `POST /teacher/student/{A}/note` mit `body` + `override_mastery=0.8` → `200`; danach existiert die Zeile in `teacher_notes`.
- [ ] Befehl: `uv run pytest tests/test_api_teacher.py -q` → grün.
- [ ] Befehl: `uv run pytest tests/test_rls.py tests/test_cohort_threshold.py -q` → weiterhin grün.
- [ ] Manuell (mit gültigem Lehrer-Token): `curl -H "Authorization: Bearer <jwt>" http://localhost:8000/teacher/student/<uuid>/mastery` → JSON-Liste mit `uncertainty`-Feld.

## Abhängigkeiten

- **API-1** — etabliert das Router-/`scoped_session`-Muster und das Mount in `main.py`, auf dem die Teacher-Endpoints aufbauen.
- **RET-4** — `skill_mastery_distribution` (→ `enforce_min_cohort`) für den Distribution-Endpoint; ohne diese Funktion gibt es keinen Min-Cohort-geschützten Aggregat-Pfad.
- Implizit **SAF-1/SAF-3** — RLS-Policies `teacher_*_in_class` + `enforce_min_cohort` müssen live sein; **DB-3-Ergänzung** (`app.current_teacher_id` in `scoped_session`).
- **API-3** — Schemas `SkillMastery`/`CohortStat` + Fehlermodell (`CohortTooSmall` → `403`).

**Nachgelagert:** **FE-T1/FE-T2/FE-T3** (Lehrer-Dashboard, Open Learner Model, Interventions-Steuerung) und **TST-4** (E2E-Smoke: Lehrer sieht Stand inkl. Unsicherheit) bauen hierauf auf.

## Definition of Done

- [ ] Akzeptanzkriterien dieses Tasks erfüllt (drei Endpoints, RLS-gefiltert, Min-Cohort, Notiz/Override).
- [ ] Tests grün inkl. der Safety-Tests (`test_rls.py`, `test_cohort_threshold.py`) — dieser Task ist `safety-critical`.
- [ ] Keine PII in externen LLM-Prompts (kein LLM-Call hier); zusätzlich: kein Notiz-Freitext in der URL (Body statt Query-Param), P4.
- [ ] `uv`-only, keine `pip`-Aufrufe.
- [ ] GitHub-Issue API-2 geschlossen, E9-Epic-Checkliste aktualisiert.

