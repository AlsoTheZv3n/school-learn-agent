## Ziel

Der interpretierbare BKT-Kern als reine, DB-freie Python-/NumPy-Funktionen: `posterior`, `update`, `mastery_after` plus die `BKTParams`-Dataclass. Am Ende lässt sich aus einer Sequenz von korrekt/falsch-Beobachtungen deterministisch eine Mastery in [0,1] berechnen — ohne Seiteneffekte und ohne Datenbank.

## Kontext & Prinzipien

- **P5 — Open Learner Model (interpretierbar):** BKT wird gewählt, weil eine Lehrperson *nachvollziehen* können muss, warum das System ein Kind als (nicht) gemeistert einschätzt. Vier benannte Wahrscheinlichkeiten (prior/learn/slip/guess) sind menschenlesbar — anders als eine neuronale Black-Box. Dieser Task legt genau diese transparenten Parameter offen.
- **P3 — Das Modell verbessert sich, nicht der Agent:** Diese Funktionen sind die *Mathematik* der Modell-Aktualisierung. Sie sind deterministisch und auditierbar — kein LLM, keine Selbstmodifikation.
- **P7 — Genau eine Plugin-Naht (`grading`):** `learner_model/` ist bewusst ein **flaches Modul**, keine Strategy/Registry. Diese Datei darf KEINE Plugin-/Adapter-Struktur einführen.
- **P9 — `uv` ausschliesslich:** `numpy` ist bereits in `apps/api/pyproject.toml` deklariert; falls etwas fehlt, via `uv add` — niemals `pip`.

## Zu erstellende/ändernde Dateien

- `apps/api/src/its/learner_model/bkt.py` (neu) — die reinen Funktionen + `BKTParams`.
- `apps/api/tests/test_bkt.py` bzw. `tests/test_bkt.py` (neu) — Unit-Tests (siehe Tests). Verortung gemäss Repository-Layout: Tests liegen unter `tests/`.

> Hinweis: zu entscheiden — ob `learner_model/__init__.py` angelegt/ergänzt wird. Das Layout in docs/00 §6 listet `learner_model/` als Modul; ein leeres `__init__.py` ist üblich, aber nicht explizit spezifiziert.

## Schnittstellen & Signaturen

Reproduktion aus docs/06 (`learner_model/bkt.py`, reine Funktionen, NumPy):

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

Parameter-Bedeutung (aus docs/06):

| Parameter | Bedeutung |
|---|---|
| `p_init` (prior) | P(Skill anfangs gekonnt) |
| `p_learn` (transit) | P(Lernen pro Gelegenheit) |
| `p_slip` | P(Fehler trotz Können) |
| `p_guess` | P(Treffer trotz Nicht-Können) |

## Umsetzungsschritte

- [ ] `apps/api/src/its/learner_model/bkt.py` anlegen.
- [ ] `BKTParams` als `@dataclass(frozen=True)` mit den Default-Werten `p_init=0.2`, `p_learn=0.15`, `p_slip=0.10`, `p_guess=0.20` definieren.
- [ ] `posterior(p_known, correct, p)` exakt wie oben implementieren — inkl. des `den > 0`-Guards gegen Division durch 0 (Rückgabe `p_known`, falls Nenner 0).
- [ ] `update(p_known, correct, p)` implementieren: erst `posterior`, dann Lern-Transition `post + (1-post)*p.p_learn`.
- [ ] `mastery_after(sequence, p)` implementieren: Start bei `p.p_init`, über die Sequenz falten.
- [ ] Modul-Docstring ergänzen, der die vier Parameter erklärt (P5 — Lesbarkeit für Reviewer).
- [ ] Sicherstellen, dass KEINE DB-/IO-/LLM-Importe enthalten sind (Reinheit, schnelle Unit-Tests).
- [ ] `tests/test_bkt.py` mit Range-, Monotonie- und Vergleichstests anlegen.
- [ ] Einen fixierten Referenzwert berechnen und als Assertion festhalten (siehe offene Frage / Hinweis).
- [ ] `uv run ruff check` und `uv run pytest tests/test_bkt.py` lokal grün.

> Hinweis: zu entscheiden — der Doc fordert „bekannte Referenzwerte für eine kurze Sequenz", nennt aber keine Zahl. Konkreten Wert (z. B. `mastery_after([True], BKTParams())`) einmal berechnen und als Konstante fixieren, statt einen zu erfinden.

> Hinweis: zu entscheiden — ob `mastery` defensiv auf [0,1] geklemmt wird (numerisch kann minimal über 1.0 driften). Doc sieht kein Clamping vor; Property-Test prüft den Bereich.

## Akzeptanzkriterien

- [ ] `posterior(p_known, correct, p)` liefert für beide `correct`-Fälle Werte in `[0,1]` (abgeleitet aus AK „Werte in [0,1]").
- [ ] BKT-Update ist korrekt: `mastery_after([True, True, True]) > mastery_after([True])` (monotone Tendenz: mehr Korrekte → höhere Mastery).
- [ ] `mastery_after([False, False]) < mastery_after([True, True])` (falsch hebt Mastery nicht über korrekt).
- [ ] Ein fixierter Referenzwert für eine kurze Sequenz wird per Test bestätigt.
- [ ] Keine DB- oder LLM-Abhängigkeit im Modul (reine Funktionen).
- [ ] `learner_model/` bleibt ein flaches Modul ohne Plugin-Registry (P7).

## Tests / Verifikation

```bash
cd apps/api
uv run pytest tests/test_bkt.py -q
```

Erwartet: alle Tests grün, schnell (keine DB-Verbindung nötig). Beispiel-Assertions (aus docs/10 §4):

```python
from its.learner_model.bkt import posterior, update, mastery_after, BKTParams

def test_posterior_in_range():
    p = BKTParams()
    assert 0.0 <= posterior(0.3, True, p) <= 1.0
    assert 0.0 <= posterior(0.3, False, p) <= 1.0

def test_correct_increases_mastery():
    p = BKTParams()
    assert mastery_after([True, True, True], p) > mastery_after([True], p)

def test_wrong_does_not_exceed_correct():
    p = BKTParams()
    assert mastery_after([False, False], p) < mastery_after([True, True], p)
```

## Abhängigkeiten

- **FND-2** (uv-Projekt mit `numpy>=2.1` in `pyproject.toml`) — Voraussetzung, damit das Modul samt Tests via `uv run` lauffähig ist.
- Nachgelagert: **LM-2** importiert `update` und `BKTParams` aus diesem Modul; **TST-2** verlässt sich auf die hier definierten Signaturen.

## Definition of Done

- [ ] Akzeptanzkriterien dieses Tasks erfüllt (Range, Monotonie, Referenzwert).
- [ ] Tests grün (`uv run pytest tests/test_bkt.py`); keine Safety-Tests betroffen (reine Logik).
- [ ] Keine PII in externen LLM-Prompts — N/A (kein LLM-Pfad in diesem Task).
- [ ] `uv`-only, keine `pip`-Aufrufe.
- [ ] Zugehöriges GitHub-Issue (LM-1) geschlossen, Epic-Checkliste E6 aktualisiert.
