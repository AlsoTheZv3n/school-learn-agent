## Ziel

`_simulate_history` erzeugt pro Schüler:in eine **nicht-uniforme**, plausible Lernhistorie: aus einer latenten Fähigkeit (Beta-Verteilung) und einem Übungsfortschritt werden `attempts` generiert, und die Mastery wird über **denselben** Tracing-Service (`record_attempt`, LM-2) abgeleitet wie im Echtbetrieb. Das `load`-Profil erzeugt dadurch Kohorten mit `n >= MIN_COHORT_K`, sodass die Population-/Aggregat-Endpoints (RET-4) testbar werden.

## Kontext & Prinzipien

- **P3 (Das Learner-Modell verbessert sich, nicht der Agent):** Die Mastery wird NICHT direkt in `learner_state` geschrieben, sondern ausschließlich über `record_attempt` abgeleitet — identisch zur Live-Logik. So sind Demo-Verteilungen konsistent mit dem realen Modellverhalten.
- **P5 (Open Learner Model):** Uniform-zufällige Antworten würden zu unbrauchbaren, gleichförmigen Mastery-Werten führen; das Open Learner Model wirkte im Demo unecht. Die latente-Fähigkeit-Modellierung erzeugt eine glaubwürdige Streuung inkl. Unsicherheit (`uncertainty` aus `record_attempt`).
- **Konsistenz mit RET-4 (Min-Cohort, docs/05):** Das `load`-Profil muss Kohorten oberhalb der Schwelle `k` (`MIN_COHORT_K`, Default 10) erzeugen, sonst werfen die Population-Aggregate `CohortTooSmall` und sind nicht testbar.
- **P9 (`uv` ausschließlich):** Ausführung und Tests über `uv run`.

## Zu erstellende/ändernde Dateien

- `scripts/seed.py` — `_simulate_history(...)` implementieren (Datei aus MOCK-1).
- Nutzt `apps/api/src/its/learner_model/tracing.py` (`record_attempt`) und `apps/api/src/its/db/models.py` (`Attempt`) — keine Änderung an diesen Dateien.

## Schnittstellen & Signaturen

Referenz-Implementierung aus docs/11 (A.2) — autark zu reproduzieren:

```python
from its.learner_model.tracing import record_attempt
from its.db.models import Attempt

def _simulate_history(s, student, skills, rng=random.Random()):
    ability = rng.betavariate(2, 2)              # latente Fähigkeit je Schüler:in (0..1)
    for skill in skills:
        n = rng.randint(4, 12)                   # Versuche je Skill
        for i in range(n):
            # Lernfortschritt: P(correct) steigt mit Übung, gedeckelt durch ability
            p_correct = min(0.95, ability * (0.5 + 0.05 * i))
            correct = rng.random() < p_correct
            s.add(Attempt(student_id=student.id, skill_id=skill.id,
                          item_ref=f"seed-{skill.key}-{i}", is_correct=correct))
            record_attempt(s, student.id, skill.id, correct)   # gleiche Logik wie live
```

Signatur des konsumierten Tracing-Service (LM-2, docs/06 A.2):

```python
def record_attempt(session: Session, student_id, skill_id, correct: bool,
                   params: BKTParams | None = None) -> LearnerState:
    p = params or BKTParams()
    state = session.get(LearnerState, {"student_id": student_id, "skill_id": skill_id})
    if state is None:
        state = LearnerState(student_id=student_id, skill_id=skill_id,
                             mastery=p.p_init, uncertainty=1.0, attempts_count=0)
        session.add(state)
    state.mastery = update(state.mastery, correct, p)   # BKT-Update
    state.attempts_count += 1
    state.uncertainty = 1.0 / (state.attempts_count + 1)
    return state
```

Min-Cohort-Schwelle, die das `load`-Profil erfüllen muss (SAF-3, docs/04 §4):

```python
def enforce_min_cohort(n: int, payload: dict, k: int | None = None) -> CohortResult:
    threshold = k if k is not None else settings.min_cohort_k   # Default 10
    if n < threshold:
        raise CohortTooSmall(f"cohort n={n} below threshold k={threshold}")
    return CohortResult(n=n, payload=payload)
```

## Umsetzungsschritte

- [ ] `_simulate_history(s, student, skills, rng)` gemäß Referenz implementieren.
- [ ] Latente Fähigkeit `ability = rng.betavariate(2, 2)` je Schüler:in ziehen (einmal pro Schüler:in, nicht pro Skill).
- [ ] Pro Skill `n = rng.randint(4, 12)` Versuche; `p_correct = min(0.95, ability * (0.5 + 0.05 * i))`; `correct = rng.random() < p_correct`.
- [ ] Pro Versuch ein `Attempt(...)` mit `item_ref=f"seed-{skill.key}-{i}"` einfügen UND `record_attempt(s, student.id, skill.id, correct)` aufrufen (kein Direktschreiben von `learner_state`).
- [ ] `rng` deterministisch seedbar machen (Vorschlag: `--seed`-CLI-Argument aus MOCK-1 durchreichen, Default fix), damit Demos/Tests reproduzierbar sind.
- [ ] Im `load`-Profil sicherstellen/validieren, dass `students_per_class >= MIN_COHORT_K` (Default 10); bei Unterschreitung warnen, damit RET-4-Aggregate nicht `CohortTooSmall` werfen.
- [ ] Performance für große `load`-Läufe berücksichtigen: ggf. periodische `s.flush()`/Batch-Commits, ohne den Tracing-Service zu umgehen.

## Akzeptanzkriterien

- [ ] Mastery-Verläufe sind plausibel und **nicht uniform** (Streuung über Schüler:innen erkennbar); jeder `learner_state.mastery` liegt in `[0,1]`.
- [ ] `learner_state` wird ausschließlich über `record_attempt` befüllt (kein direkter Insert/Update in `learner_state` im Seeder).
- [ ] `attempts` und `learner_state` sind nach dem Lauf konsistent (jeder Skill mit Versuchen hat einen `learner_state`-Eintrag mit passendem `attempts_count`).
- [ ] `--profile load` erzeugt pro Klasse eine Kohorte mit `n >= MIN_COHORT_K`, sodass die Population-Aggregate (RET-4) NICHT `CohortTooSmall` werfen.

## Tests / Verifikation

```bash
cd apps/api
DATA_MODE=mock uv run python ../../scripts/seed.py --profile load --classes 5 --students-per-class 24
# Optional: bestehende Population-/Cohort-Tests
DATA_MODE=mock uv run pytest -q tests/test_cohort_threshold.py
```

Erwartete Ergebnisse:
- `learner_state.mastery` zeigt eine erkennbare Verteilung (z. B. Varianz deutlich > 0; nicht alle Werte gleich) — prüfbar via Aggregat-Query `SELECT min(mastery), avg(mastery), max(mastery), stddev(mastery) FROM learner_state;`.
- Für jede der 5 Klassen liefert `skill_mastery_distribution(class_id, skill_id)` ein Ergebnis mit `n >= 10` (kein `CohortTooSmall`).
- Alle Mastery-Werte in `[0,1]`.

> Hinweis: zu entscheiden — exakte CLI-Flagge/Default für reproduzierbares RNG (`--seed`), siehe Epic-Planung offene Frage 1.

## Abhängigkeiten

- **MOCK-1** (Seeder-CLI): liefert das Gerüst, den Aufruf-Rahmen von `_simulate_history` und die Profil-/Session-Logik.
- **LM-2** (`record_attempt`, transitiv über MOCK-1): die zentrale Schnittstelle, über die Mastery abgeleitet wird — Konsistenz mit dem Live-Pfad (P3).
- Nachgelagert: **RET-4** (Population-Tests, docs/05) benötigt die vom `load`-Profil erzeugten Kohorten `>= k`.

## Definition of Done

- [ ] Akzeptanzkriterien (oben, abgeleitet aus docs/11 A.2) erfüllt.
- [ ] Tests grün, inkl. Nachweis der nicht-uniformen Verteilung und der Kohortengröße im `load`-Profil.
- [ ] Kein LLM betroffen; keine PII in externen Prompts (n/a).
- [ ] `uv`-only; keine `pip`-Aufrufe.
- [ ] GitHub-Issue MOCK-2 geschlossen, Epic-E13-Checkliste aktualisiert.

