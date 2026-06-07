## Ziel

Der **Math-Grader** prüft eine Schülerantwort symbolisch/numerisch gegen den **kuratierten** Answer Key und liefert ein deterministisches `GradeResult` mit `confidence = 1.0`. Äquivalente Schreibweisen (z. B. `x^2+2*x+1` vs. `(x+1)^2`) werden als richtig erkannt; unparsbare Eingaben werden sauber abgefangen.

## Kontext & Prinzipien

- **P2 — Kuratierte Antworten, generative Freiheit nur wo Fehler sichtbar sind**: Der Math-Grader prüft gegen `item.answer_key`, der **kuratiert** ist. Es findet **keine** LLM-Generierung des Schlüssels statt. Ein halluzinierter Antwortschlüssel würde ein Kind falsch unterrichten — deshalb ist dieser Pfad rein deterministisch und meldet `confidence = 1.0`.
- **P7 — Plugin-Naht**: `MathGrader` ist eine konkrete `GraderStrategy` (`subject_key = "math"`) und wird über die Registry aus GR-1 angemeldet — keine eigene Plugin-Mechanik.
- **P9 — `uv` ausschliesslich**: `sympy` ist bereits in `apps/api/pyproject.toml` (FND-2) als Dependency gelistet (`sympy>=1.13`). Falls weiteres nötig, `uv add` — niemals `pip`.
- Diese Task ist `priority:critical`, weil sie die P2-Garantie operativ einlöst (der einzige vollständig deterministische Bewertungspfad).

## Zu erstellende/aendernde Dateien

Gemäss Repository-Layout (docs/00, Section 6, `grading/ ... math/...`):

- `apps/api/src/its/grading/math.py` — (neu) `MathGrader`.
- `apps/api/src/its/grading/__init__.py` — (ändern) `register(MathGrader())` beim Import.
- `apps/api/tests/test_grading/test_math.py` — (neu) Math-Grader-Tests.

## Schnittstellen & Signaturen

`apps/api/src/its/grading/math.py` (exakt aus docs/06, Teil B.2):

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

Registrierung beim Start (docs/06, Teil B.3, Hinweis) in `grading/__init__.py`:

```python
from its.grading.registry import register
from its.grading.math import MathGrader
register(MathGrader())
```

Verfügbare Typen aus GR-1 (`grading/base.py`):

```python
@dataclass(frozen=True)
class Item:
    skill_key: str
    prompt: str
    answer_key: str          # KURATIERT (P2)
    rubric: str | None = None

@dataclass(frozen=True)
class GradeResult:
    correct: bool
    feedback: str
    confidence: float        # 1.0 = deterministisch geprüft
```

## Umsetzungsschritte

- [ ] `math.py` mit `MathGrader` (`subject_key = "math"`) exakt nach Spezifikation anlegen.
- [ ] `grade`: Antwort und `item.answer_key` via `sp.sympify` parsen; Äquivalenz über `bool(sp.simplify(got - expected) == 0)` bestimmen.
- [ ] Fehlerpfad: `(sp.SympifyError, TypeError)` → `GradeResult(False, "Konnte die Eingabe nicht als Term lesen.", 1.0)`.
- [ ] Feedback-Texte: `"Richtig."` bei korrekt, sonst `"Noch nicht — prüfe deine Umformung."`; `confidence` immer `1.0`.
- [ ] In `grading/__init__.py` `register(MathGrader())` ergänzen, damit der Grader beim Import angemeldet ist.
- [ ] Eingabe-Härtung prüfen (Sicherheit): SymPy-`sympify` evaluiert Ausdrücke — Eingabelänge begrenzen und/oder restriktiv parsen. > Hinweis: zu entscheiden — ob `sp.parse_expr` mit eingeschränktem `local_dict`/`transformations` statt `sympify` verwendet wird (sicherer gegen unerwartete Eingaben); im Doc steht `sympify`. Default: Doc-konform `sympify`, plus Längenlimit und Test gegen bösartige Eingaben.
- [ ] Tests in `tests/test_grading/test_math.py` schreiben (siehe unten).
- [ ] `uv run ruff check src/its/grading/math.py` ausführen.

## Akzeptanzkriterien

- [ ] Math-Grader prüft **symbolisch** gegen den **kuratierten** Key und meldet `confidence = 1.0` (docs/06 AK: „Math-Grader prüft symbolisch gegen kuratierten Key, `confidence=1.0`").
- [ ] Äquivalente Formen werden akzeptiert: `Item(skill_key="expand", prompt="(x+1)^2", answer_key="x**2 + 2*x + 1")`, `grade("x^2+2*x+1", item).correct is True`.
- [ ] Falsche Antworten werden abgelehnt: `grade("x^2+1", item).correct is False` und `.confidence == 1.0`.
- [ ] Unparsbare Eingabe ergibt `GradeResult(False, ..., 1.0)` ohne Exception.
- [ ] Keine LLM-Generierung des Schlüssels (P2) — der Pfad ist rein deterministisch.
- [ ] `MathGrader` ist beim Import über `get_grader("math")` auffindbar.

## Tests / Verifikation

```bash
cd apps/api
uv run pytest tests/test_grading/test_math.py -q
```

Erwartet: alle Tests grün. Mindestfälle (aus docs/10 §4):

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

def test_math_unparsable_input_is_safe():
    g = MathGrader()
    item = Item(skill_key="expand", prompt="(x+1)^2", answer_key="x**2 + 2*x + 1")
    res = g.grade("@@@ not a term", item)
    assert res.correct is False and res.confidence == 1.0
```

Registrierungs-Check:
```python
from its.grading.registry import get_grader
import its.grading  # löst register(MathGrader()) aus
assert get_grader("math").subject_key == "math"
```

Lint:
```bash
uv run ruff check src/its/grading/math.py   # erwartet: keine Fehler
```

## Abhaengigkeiten

- **GR-1** (`GraderStrategy`-Protokoll + Registry): GR-2 importiert `GraderStrategy`/`Item`/`GradeResult` und registriert sich über `register`.
- **Nachgelagert**:
  - **TST-2** (Unit-Tests Grading) testet den Math-Grader gegen den kuratierten Key.
  - **AG-2** (`assess_node`) ruft den Math-Grader über `get_grader("math")` auf.

## Definition of Done

(projektweite DoD aus docs/00 Section 8, auf GR-2 zugeschnitten)

- [ ] Akzeptanzkriterien aus docs/06 (GR-2) erfüllt — symbolische Prüfung gegen kuratierten Key, `confidence=1.0`.
- [ ] Tests grün (`tests/test_grading/test_math.py`), inkl. unparsbarer-Eingabe-Fall; keine Safety-Tests direkt betroffen.
- [ ] Keine PII in externen LLM-Prompts — n/a (kein LLM-Call; P2: kein LLM-generierter Schlüssel).
- [ ] `uv`-only, keine `pip`-Aufrufe (`sympy` aus `pyproject.toml`).
- [ ] Zugehöriges GitHub-Issue geschlossen, E7-Epic-Checkliste aktualisiert.
