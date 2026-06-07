## Ziel

Ein Tracing-Service `record_attempt(...)`, der ein einzelnes Antwort-Resultat (korrekt/falsch) entgegennimmt und die Tabelle `learner_state` für ein (student, skill)-Paar konsistent aktualisiert: neue Mastery via BKT, erhöhter Versuchszähler und ein grobes Unsicherheitsmass fürs Open Learner Model. Dies ist der **einzige** legitime Schreibpfad in `learner_state`.

## Kontext & Prinzipien

- **P3 — Das Modell verbessert sich, nicht der Agent:** Genau hier wird das Learner-Modell aktualisiert. Der Doc schreibt vor: „Schreibt **immer** über diesen Service (nicht direkt in `learner_state`), damit Mastery und Unsicherheit konsistent bleiben." Kein anderer Code darf `learner_state` direkt schreiben.
- **P5 — Open Learner Model:** `uncertainty` wird mitgeführt, damit die Lehrperson Mastery *mit ihrer Unsicherheit* sehen kann — keine blinde Punktschätzung.
- **P1 — Safety in der DB (RLS):** Der Service nimmt eine `Session` entgegen, die vom Aufrufer über `scoped_session` mit Rolle + `app.current_student_id` geöffnet wurde (docs/03 §5). Der Service committet NICHT selbst — die Transaktions-/RLS-Klammer gehört dem Aufrufer; so bleibt Isolation Schema-Eigenschaft statt Service-Logik.
- **P7 — flaches Modul:** keine Plugin-/Strategy-Struktur in `learner_model/`.
- **P9 — `uv` ausschliesslich.**

## Zu erstellende/ändernde Dateien

- `apps/api/src/its/learner_model/tracing.py` (neu) — `record_attempt`.
- `tests/test_tracing.py` (neu) — Integrationstest gegen die transaktionale Test-DB.
- Voraussetzung (NICHT in diesem Task zu erstellen, kommt aus DB-2): `apps/api/src/its/db/models.py` mit dem ORM-Modell `LearnerState`.

## Schnittstellen & Signaturen

Reproduktion aus docs/06 (`learner_model/tracing.py`):

```python
from sqlalchemy.orm import Session
from its.db.models import LearnerState
from its.learner_model.bkt import update, BKTParams

def record_attempt(session: Session, student_id, skill_id, correct: bool,
                   params: BKTParams | None = None) -> LearnerState:
    p = params or BKTParams()
    state = session.get(LearnerState, {"student_id": student_id, "skill_id": skill_id})
    if state is None:
        state = LearnerState(student_id=student_id, skill_id=skill_id,
                             mastery=p.p_init, uncertainty=1.0, attempts_count=0)
        session.add(state)
    state.mastery = update(state.mastery, correct, p)
    state.attempts_count += 1
    state.uncertainty = 1.0 / (state.attempts_count + 1)
    return state
```

Relevantes ORM-Modell aus docs/03 §4 (zur Orientierung; stammt aus DB-2):

```python
class LearnerState(Base):
    __tablename__ = "learner_state"
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), primary_key=True)
    skill_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("skills.id"), primary_key=True)
    mastery: Mapped[float] = mapped_column(Float, default=0.0)
    uncertainty: Mapped[float] = mapped_column(Float, default=1.0)
    attempts_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

Zugehörige DDL (docs/03 §3):

```sql
CREATE TABLE learner_state (
  student_id  uuid NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  skill_id    uuid NOT NULL REFERENCES skills(id),
  mastery     double precision NOT NULL DEFAULT 0.0,  -- P(known)
  uncertainty double precision NOT NULL DEFAULT 1.0,  -- für Open Learner Model (P5)
  attempts_count int NOT NULL DEFAULT 0,
  updated_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (student_id, skill_id)
);
```

## Umsetzungsschritte

- [ ] `apps/api/src/its/learner_model/tracing.py` anlegen mit den Importen aus dem Signatur-Block.
- [ ] `record_attempt` exakt mit der vorgegebenen Signatur implementieren.
- [ ] Default-Parameter: `p = params or BKTParams()`.
- [ ] Lookup über den zusammengesetzten Primärschlüssel: `session.get(LearnerState, {"student_id": student_id, "skill_id": skill_id})`.
- [ ] Erstanlage-Pfad: bei `None` neuen `LearnerState` mit `mastery=p.p_init`, `uncertainty=1.0`, `attempts_count=0` erzeugen und `session.add(state)`.
- [ ] Update-Pfad: `state.mastery = update(state.mastery, correct, p)`, dann `state.attempts_count += 1`, dann `state.uncertainty = 1.0 / (state.attempts_count + 1)` (Reihenfolge beachten — Unsicherheit nach dem Inkrement).
- [ ] `state` zurückgeben; **kein** `session.commit()` im Service (Transaktion gehört dem Aufrufer / `scoped_session`).
- [ ] Modul-Docstring mit dem P3-Hinweis: „einziger Schreibpfad in `learner_state`".
- [ ] `tests/test_tracing.py` schreiben (transaktionale `db`-Fixture aus docs/10 §2).
- [ ] `uv run ruff check` und der Integrationstest lokal grün.

> Hinweis: zu entscheiden — `updated_at` hat nur `server_default=func.now()` (greift bei INSERT). Beim UPDATE wird der Zeitstempel ohne `onupdate=func.now()` am Modell NICHT automatisch neu gesetzt. Entweder im Service explizit setzen oder das Modell um `onupdate` ergänzen (Modelländerung gehört strenggenommen zu DB-2). Nicht stillschweigend erfinden — als Entscheidung markieren.

> Hinweis: zu entscheiden — Verhalten von `session.get` mit Dict-PK ist SQLAlchemy-2.0-spezifisch; Test deckt das doppelte `record_attempt` ab, um den Update-Pfad (statt Doppel-INSERT) zu verifizieren.

## Akzeptanzkriterien

- [ ] `record_attempt` legt bei erstem Aufruf einen neuen `LearnerState` an (Start `mastery=p_init`, `uncertainty=1.0`).
- [ ] Bei Folgeaufrufen wird derselbe `(student, skill)`-Datensatz aktualisiert (kein zweiter Datensatz).
- [ ] `mastery` wird via BKT `update` fortgeschrieben; konsistent mit LM-1.
- [ ] `attempts_count` wird pro Aufruf um 1 erhöht.
- [ ] `uncertainty == 1.0 / (attempts_count + 1)` nach jedem Aufruf (grobes Mass fürs Open Learner Model, P5).
- [ ] Service committet nicht selbst; funktioniert innerhalb einer vom Aufrufer geöffneten (scoped) Session.
- [ ] `learner_state` wird ausschliesslich über diesen Service geschrieben (P3).

## Tests / Verifikation

Voraussetzung: Postgres läuft (z. B. `docker compose -f infra/docker-compose.yml up -d`) und Migrationen sind angewandt.

```bash
cd apps/api
uv run pytest tests/test_tracing.py -q
```

Erwartetes Testverhalten (skizziert; nutzt die `db`-Fixture aus `tests/conftest.py`):

```python
def test_record_attempt_creates_and_updates(db, seeded_student_and_skill):
    from its.learner_model.tracing import record_attempt
    student_id, skill_id = seeded_student_and_skill
    s1 = record_attempt(db, student_id, skill_id, correct=True)
    assert s1.attempts_count == 1
    assert abs(s1.uncertainty - 1.0/2) < 1e-9
    s2 = record_attempt(db, student_id, skill_id, correct=True)
    assert s2.attempts_count == 2
    assert abs(s2.uncertainty - 1.0/3) < 1e-9
    assert s2.mastery > s1.mastery   # zwei Korrekte -> höhere Mastery
```

> Hinweis: zu entscheiden — eine Fixture `seeded_student_and_skill` (Student + Skill anlegen) ist in docs/10 nicht definiert; `two_students` existiert, deckt den Fall aber nicht 1:1 ab. Kleine eigene Fixture im Test ergänzen.

## Abhängigkeiten

- **LM-1** — liefert `update` und `BKTParams`, die dieser Service importiert.
- **DB-2** — liefert das ORM-Modell `LearnerState` (und `Attempt`), in das geschrieben wird; ohne das Schema/Modell ist `record_attempt` nicht lauffähig.
- Nachgelagert: **AG-2** (`agent/nodes/update_model.py`, docs/07) ruft `record_attempt` auf und zementiert nur bei Konfidenz ≥ 0.9; **TST-3** (Agent-Turn-Integrationstest) verlässt sich auf den Schreibpfad.

## Definition of Done

- [ ] Akzeptanzkriterien dieses Tasks erfüllt (`record_attempt` aktualisiert Mastery + Unsicherheit konsistent).
- [ ] Tests grün (`uv run pytest tests/test_tracing.py`); falls Safety-Tests berührt (Schreibpfad in geschützte Tabelle), laufen `test_rls.py` weiterhin grün.
- [ ] Keine PII in externen LLM-Prompts — N/A (kein LLM-Pfad; `learner_state` enthält nur IDs/Zahlen, keine Klartext-PII, P4).
- [ ] `uv`-only, keine `pip`-Aufrufe.
- [ ] Zugehöriges GitHub-Issue (LM-2) geschlossen, Epic-Checkliste E6 aktualisiert.
