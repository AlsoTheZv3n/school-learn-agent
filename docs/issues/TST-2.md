## Ziel

DB-freie, schnelle Unit-Tests für die reine Kernlogik: BKT (`tests/test_bkt.py`), Math-Grader gegen den **kuratierten** Answer Key (`tests/test_grading/test_math.py`), Content-Parser (`tests/test_content_parser.py`) und Anonymizer (`tests/test_anonymize.py`). Damit ist die unterste, breite Ebene der Pyramide abgedeckt.

## Kontext & Prinzipien

- **P2 (Kuratierte Antworten):** Der Math-Grader-Test prüft, dass die Bewertung gegen einen **kuratierten** `answer_key` läuft und `confidence == 1.0` liefert (deterministisch geprüft, nicht LLM-halluziniert). Genau das schützt ein Kind vor falscher Unterrichtung.
- **P7 (genau eine Plugin-Naht):** Grading ist der einzige Strategy/Adapter-Punkt. Die Grader-Tests sichern diese Naht ab (Registry-Lookup, Fach-Keying), ohne andere Module zu pluginisieren.
- **P4 (PII verlässt die Maschine nicht im Klartext):** `test_anonymize.py` beweist, dass Name/Datum/E-Mail vor jedem externen Call durch `scrub` ersetzt werden.
- **Schnell & DB-frei (docs/10 §1):** Diese Tests dürfen **keine** DB anfassen — reine Funktionen, schnelles Feedback.

## Zu erstellende/ändernde Dateien

- `tests/test_bkt.py` — neu.
- `tests/test_grading/__init__.py` — neu (Package-Marker).
- `tests/test_grading/test_math.py` — neu.
- `tests/test_content_parser.py` — neu.
- `tests/test_anonymize.py` — neu.

## Schnittstellen & Signaturen

**BKT** (`apps/api/src/its/learner_model/bkt.py`, docs/06 A.1 — autark reproduziert):

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class BKTParams:
    p_init: float = 0.2
    p_learn: float = 0.15
    p_slip: float = 0.10
    p_guess: float = 0.20

def posterior(p_known: float, correct: bool, p: BKTParams) -> float: ...
def update(p_known: float, correct: bool, p: BKTParams) -> float: ...
def mastery_after(sequence: list[bool], p: BKTParams) -> float: ...
```

`tests/test_bkt.py` (docs/10 §4 — autark):

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

**Grading** (`apps/api/src/its/grading/base.py`, docs/06 B.1 — autark):

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

`MathGrader` (`apps/api/src/its/grading/math.py`, docs/06 B.2) nutzt `sympy`: `subject_key = "math"`, `grade(answer, item) -> GradeResult` mit `confidence=1.0`.

Registry (`apps/api/src/its/grading/registry.py`, docs/06 B.1): `register(grader)`, `get_grader(subject_key)` → `LookupError` bei unbekanntem Fach.

`tests/test_grading/test_math.py` (docs/10 §4 — autark):

```python
from its.grading.math import MathGrader
from its.grading.base import Item

def test_math_equivalent_forms_accepted():
    g = MathGrader()
    item = Item(skill_key="expand", prompt="(x+1)^2", answer_key="x**2 + 2*x + 1")
    assert g.grade("x^2+2*x+1", item).correct is True

def test_math_wrong_rejected():
    g = MathGrader()
    item = Item(skill_key="expand", prompt="(x+1)^2", answer_key="x**2 + 2*x + 1")
    res = g.grade("x^2+1", item)
    assert res.correct is False and res.confidence == 1.0
```

**Anonymizer** (`apps/api/src/its/llm/anonymize.py`, docs/07 §4 — autark):

```python
import re
_PATTERNS = [
    (re.compile(r"\b[A-ZÄÖÜ][a-zäöü]+\s[A-ZÄÖÜ][a-zäöü]+\b"), "[NAME]"),
    (re.compile(r"\b\d{2}\.\d{2}\.\d{4}\b"), "[DATE]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[EMAIL]"),
]
def scrub(text: str) -> str: ...
```

**Content-Parser** (`apps/api/src/its/content/parser.py`, docs/00 §6 / docs/01 CON-1): trennt Prosa von ```sql/```cypher-Codeblöcken und extrahiert `[[wikilinks]]` als Kanten.

> Hinweis: zu entscheiden — die genaue Signatur von `content/parser.py` (Funktionsname, Rückgabetyp) ist in den Docs nur funktional beschrieben (Prosa/Code-Split + Wikilink-Extraktion), nicht als Codeauszug. Test gegen die tatsächlich von CON-1 implementierte API schreiben.

## Umsetzungsschritte

- [ ] `tests/test_bkt.py` mit den drei Tests (Range, Monotonie, Korrekt > Falsch) anlegen.
- [ ] Optional: Referenzwert-Test für eine kurze Sequenz (bekannter Erwartungswert, mit `pytest.approx`).
- [ ] `tests/test_grading/__init__.py` anlegen (Package-Marker).
- [ ] `tests/test_grading/test_math.py`: äquivalente Form akzeptiert; falsche zurückgewiesen mit `confidence == 1.0`.
- [ ] **Registry-Test (P7):** `register(MathGrader())`, `get_grader("math")` liefert `MathGrader`; unbekanntes Fach ⇒ `LookupError`.
- [ ] **Robustheit:** unparsbare Eingabe (z. B. `"x^^"`) ⇒ `correct is False`, `confidence == 1.0`, neutrale Meldung (kein Crash).
- [ ] `tests/test_anonymize.py`: `scrub` ersetzt Name (`"Sven Weidenmann"` → enthält `[NAME]`), Datum (`"01.02.2014"` → `[DATE]`), E-Mail (`"a@b.ch"` → `[EMAIL]`); reiner Skill-Key bleibt unverändert.
- [ ] `tests/test_content_parser.py`: Prosa wird ohne Codeblöcke zurückgegeben; ein ```sql-Block landet als Sidecar/Code, nicht in der Prosa; `[[wikilink]]` wird als Kante extrahiert.
- [ ] Sicherstellen: **keine** dieser Tests importiert `db`/`engine` oder benötigt `DATABASE_URL`.

## Akzeptanzkriterien

- [ ] BKT-Unit-Tests grün: `posterior` in `[0,1]`; mehr Korrekte ⇒ höhere Mastery; falsche Sequenz < korrekte Sequenz.
- [ ] Math-Grader akzeptiert äquivalente Formen, weist falsche zurück, `confidence == 1.0` (P2).
- [ ] Registry liefert den Math-Grader für `"math"`; unbekanntes Fach ⇒ `LookupError` (P7).
- [ ] `scrub` ersetzt Name/Datum/E-Mail (P4); test grün.
- [ ] Content-Parser trennt Prosa/Code und extrahiert Wikilinks; test grün.
- [ ] Alle Tests laufen **ohne** DB und schnell.

## Tests / Verifikation

```bash
cd apps/api && uv sync
uv run pytest tests/test_bkt.py tests/test_grading/ tests/test_content_parser.py tests/test_anonymize.py -q
```

Erwartet: alle Tests `passed`, Laufzeit klein (Sekundenbereich), **keine** DB-Verbindung nötig (laufen auch ohne `DATABASE_URL`/laufende Postgres-Instanz). Beispiel-Assertions, die grün sein müssen: `g.grade("x^2+2*x+1", item).correct is True`; `g.grade("x^2+1", item).confidence == 1.0`; `"[NAME]" in scrub("Frau Meier schreibt")`.

## Abhängigkeiten

- **LM-1 (BKT-Kern):** Testgegenstand für `test_bkt.py` — die reinen Funktionen `posterior`/`update`/`mastery_after`.
- **GR-2 (Math-Grader):** Testgegenstand für `test_grading/test_math.py` — symbolische Prüfung gegen den kuratierten Key.
- (implizit) GR-1 (Protocol+Registry), CON-1 (Parser), AG-3 (Anonymizer) liefern die übrigen Testgegenstände.
- **Nachgelagert:** TST-3 baut auf demselben Grader/BKT auf, jetzt integriert über den Agent-Loop.

## Definition of Done

- [ ] Akzeptanzkriterien aus docs/10 §8 (Unit-Teil) erfüllt: BKT- und Grading-Unit-Tests grün; Parser/Anonymizer getestet.
- [ ] Tests grün; Safety-Tests nicht direkt betroffen, müssen aber weiterhin grün sein.
- [ ] Keine PII in externen LLM-Prompts — durch `test_anonymize.py` aktiv abgesichert (P4).
- [ ] `uv`-only, keine `pip`-Aufrufe.
- [ ] Zugehöriges GitHub-Issue (TST-2) geschlossen, Epic-Checkliste (E12) aktualisiert.
