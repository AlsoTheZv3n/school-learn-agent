# 06 — Learner-Modell & Grading (E6, E7, M3)

**Ziel:** Das interpretierbare Lernmodell (BKT) plus die fachspezifische Bewertung als einzige
Plugin-Naht (P7). Beide getrennt, beide getestet.

**Voraussetzungen:** DB-2 (Modelle), FND-2.
**Issues:** LM-1 … LM-3 (Lernmodell), GR-1 … GR-3 (Grading).

---

## Teil A — Learner-Modell (E6)

### A.1 BKT-Kern (LM-1)

Bayesian Knowledge Tracing: pro Skill vier Wahrscheinlichkeiten. Interpretierbar (P5),
funktioniert mit dünnen Daten, kein Trainingskorpus nötig.

| Parameter | Bedeutung |
|---|---|
| `p_init` (prior) | P(Skill anfangs gekonnt) |
| `p_learn` (transit) | P(Lernen pro Gelegenheit) |
| `p_slip` | P(Fehler trotz Können) |
| `p_guess` | P(Treffer trotz Nicht-Können) |

`apps/api/src/its/learner_model/bkt.py` (reine Funktionen, NumPy):

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class BKTParams:
    p_init: float = 0.2
    p_learn: float = 0.15
    p_slip: float = 0.10
    p_guess: float = 0.20

def posterior(p_known: float, correct: bool, p: BKTParams) -> float:
    """P(known | Beobachtung) per Bayes."""
    if correct:
        num = p_known * (1 - p.p_slip)
        den = num + (1 - p_known) * p.p_guess
    else:
        num = p_known * p.p_slip
        den = num + (1 - p_known) * (1 - p.p_guess)
    return num / den if den > 0 else p_known

def update(p_known: float, correct: bool, p: BKTParams) -> float:
    """Ein Lernschritt: Posterior, dann Lern-Transition."""
    post = posterior(p_known, correct, p)
    return post + (1 - post) * p.p_learn

def mastery_after(sequence: list[bool], p: BKTParams) -> float:
    pk = p.p_init
    for correct in sequence:
        pk = update(pk, correct, p)
    return pk
```

**Tests (LM-1):** monotone Tendenz (mehr Korrekte → höhere Mastery); `posterior` in `[0,1]`;
bekannte Referenzwerte für eine kurze Sequenz.

### A.2 Tracing-Service (LM-2)

Nimmt ein `attempt`-Resultat, aktualisiert `learner_state`. `uncertainty` als grobes Mass
(z. B. `min(1, 1/(attempts_count+1))`) für das Open Learner Model.

`apps/api/src/its/learner_model/tracing.py`:

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

> Schreibt **immer** über diesen Service (nicht direkt in `learner_state`), damit Mastery und
> Unsicherheit konsistent bleiben (P3: das Modell aktualisiert sich, nicht der Agent).

### A.3 DKT-Platzhalter (LM-3)

`apps/api/src/its/learner_model/dkt.py`: interface-kompatibler Stub + Doku „erst aktivieren,
wenn genügend Interaktionshistorie vorliegt **und** BKT messbar limitiert" (P2/P5).

---

## Teil B — Grading (E7) · **Plugin-Naht (P7)**

Dies ist der **einzige** Strategy/Adapter-Punkt. Begründung: erweiterbar durch Dritte,
strukturell ähnliche aber inhaltlich diverse Fälle, separate Versionierung denkbar.

### B.1 Protokoll + Registry (GR-1)

`apps/api/src/its/grading/base.py`:

```python
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class Item:
    skill_key: str
    prompt: str
    answer_key: str          # KURATIERT (P2) — nicht vom LLM erzeugt
    rubric: str | None = None

@dataclass(frozen=True)
class GradeResult:
    correct: bool
    feedback: str
    confidence: float        # 1.0 = deterministisch geprüft

class GraderStrategy(Protocol):
    subject_key: str
    def grade(self, answer: str, item: Item) -> GradeResult: ...
```

`apps/api/src/its/grading/registry.py`:

```python
from its.grading.base import GraderStrategy

_REGISTRY: dict[str, GraderStrategy] = {}

def register(grader: GraderStrategy) -> None:
    _REGISTRY[grader.subject_key] = grader

def get_grader(subject_key: str) -> GraderStrategy:
    try:
        return _REGISTRY[subject_key]
    except KeyError as e:
        raise LookupError(f"no grader registered for subject '{subject_key}'") from e
```

### B.2 Math-Grader (GR-2)

Symbolische/numerische Prüfung gegen den **kuratierten** Answer Key. **Keine** LLM-Generierung
des Schlüssels.

`apps/api/src/its/grading/math.py`:

```python
import sympy as sp
from its.grading.base import GraderStrategy, Item, GradeResult

class MathGrader:
    subject_key = "math"
    def grade(self, answer: str, item: Item) -> GradeResult:
        try:
            got = sp.sympify(answer)
            expected = sp.sympify(item.answer_key)
            correct = bool(sp.simplify(got - expected) == 0)
        except (sp.SympifyError, TypeError):
            return GradeResult(False, "Konnte die Eingabe nicht als Term lesen.", 1.0)
        return GradeResult(correct,
                           "Richtig." if correct else "Noch nicht — prüfe deine Umformung.",
                           1.0)
```

### B.3 Language- & History-Grader (GR-3)

- `grading/language.py`: regelbasiert (z. B. erwartete Formen/Vokabeln); deterministisch wo möglich.
- `grading/history.py`: offene Antwort. LLM darf einen Bewertungs**vorschlag** machen (Rubric-gestützt),
  aber `confidence < 1.0` und **Lehrer-Override** ist vorgesehen (P6). Das Resultat wird nie als
  endgültig „korrekt/falsch" ohne menschliche Bestätigung in `learner_state` zementiert, wenn die
  Konfidenz niedrig ist.

> Registrierung beim Start (z. B. in `grading/__init__.py`):
> ```python
> from its.grading.registry import register
> from its.grading.math import MathGrader
> register(MathGrader())
> ```

---

## Akzeptanzkriterien (gesamt)

- [ ] BKT-Update korrekt, Werte in `[0,1]`, monotone Tendenz (LM-1)
- [ ] `record_attempt` aktualisiert Mastery + Unsicherheit konsistent (LM-2)
- [ ] DKT-Stub interface-kompatibel + Aktivierungs-Doku (LM-3)
- [ ] `GraderStrategy`-Protokoll + Registry, gekeyt auf Fach (GR-1)
- [ ] Math-Grader prüft symbolisch gegen kuratierten Key, `confidence=1.0` (GR-2)
- [ ] Language/History-Grundgerüst; History mit Lehrer-Override-Pfad (GR-3)
- [ ] Nur `grading/` ist Plugin-Registry; Lernmodell bleibt flache Module (P7)

---

## Claude-Code-Prompt

```
Setze E6 + E7 (docs/06-learner-model-and-grading.md) um: learner_model/bkt.py (reine
NumPy-Funktionen posterior/update/mastery_after), learner_model/tracing.py (record_attempt,
schreibt learner_state inkl. uncertainty), learner_model/dkt.py (Stub + Doku). Dann
grading/base.py (GraderStrategy-Protocol, Item mit kuratiertem answer_key), grading/registry.py,
grading/math.py (sympy gegen Key, confidence=1.0) und Grundgerüste grading/language.py +
grading/history.py (History mit niedriger Konfidenz + Lehrer-Override). Registriere die Grader
beim Start. Schreibe tests/test_bkt.py und tests/test_grading/. Halte P2/P3/P7 strikt ein.
Schliesse LM-1..3 und GR-1..3.
```
