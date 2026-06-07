## Ziel

Die **Grundgerüste** für zwei weitere Fächer stehen: ein regelbasierter `LanguageGrader` (deterministisch wo möglich) und ein `HistoryGrader` für offene Antworten, der einen LLM-*Vorschlag* mit `confidence < 1.0` liefert und einen **Lehrer-Override**-Pfad vorsieht. Beide werden über die Registry (GR-1) angemeldet.

## Kontext & Prinzipien

- **P2 — Kuratierte Antworten / generative Freiheit nur wo Fehler sichtbar sind**: Sprache wird regelbasiert gegen erwartete Formen geprüft (deterministisch). Geschichte ist offen; ein LLM darf nur einen **Bewertungsvorschlag** machen (Rubric-gestützt), niemals die „Wahrheit" erfinden.
- **P6 — Mensch im Loop ist Sicherheitsarchitektur**: Bei niedriger Konfidenz wird das Resultat **nie** ohne menschliche Bestätigung in `learner_state` zementiert. History setzt deshalb strukturell `confidence < 1.0`, damit die downstream-Schwelle (`>= 0.9` in AG-2/`update_model_node`) den Eintrag zurückhält und an die Lehrperson übergibt.
- **P4 — PII verlässt die Maschine nicht im Klartext**: History darf den LLM nur über den anonymisierenden Client (`its.llm.client.complete`, AG-3) aufrufen, der vor jedem externen Call `scrub` anwendet. Roher Schüler-Antworttext geht **nie** direkt an eine externe API.
- **P7 — Plugin-Naht**: `LanguageGrader` und `HistoryGrader` sind konkrete `GraderStrategy`-Implementierungen, registriert über GR-1 — keine eigene Mechanik.
- **P9 — `uv` ausschliesslich**.

## Zu erstellende/aendernde Dateien

Gemäss Repository-Layout (docs/00, Section 6, `grading/ ... language/history`):

- `apps/api/src/its/grading/language.py` — (neu) `LanguageGrader`.
- `apps/api/src/its/grading/history.py` — (neu) `HistoryGrader`.
- `apps/api/src/its/grading/__init__.py` — (ändern) `register(LanguageGrader())` und `register(HistoryGrader())`.
- `apps/api/tests/test_grading/test_language.py` und `apps/api/tests/test_grading/test_history.py` — (neu).

## Schnittstellen & Signaturen

Vorgaben aus docs/06, Teil B.3:

- `grading/language.py`: regelbasiert (z. B. erwartete Formen/Vokabeln); deterministisch wo möglich.
- `grading/history.py`: offene Antwort. LLM darf einen Bewertungs**vorschlag** machen (Rubric-gestützt), aber `confidence < 1.0` und **Lehrer-Override** ist vorgesehen (P6). Das Resultat wird nie als endgültig „korrekt/falsch" ohne menschliche Bestätigung in `learner_state` zementiert, wenn die Konfidenz niedrig ist.

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

class GraderStrategy(Protocol):
    subject_key: str
    def grade(self, answer: str, item: Item) -> GradeResult: ...
```

Gerüst (Skizze, an die Signaturen gebunden):

```python
# grading/language.py
from its.grading.base import Item, GradeResult

class LanguageGrader:
    subject_key = "language"
    def grade(self, answer: str, item: Item) -> GradeResult:
        # deterministischer, normalisierter Vergleich gegen item.answer_key
        norm = lambda s: " ".join(s.strip().lower().split())
        correct = norm(answer) == norm(item.answer_key)
        return GradeResult(correct,
                           "Richtig." if correct else "Noch nicht — achte auf die erwartete Form.",
                           1.0)
```

```python
# grading/history.py
from its.grading.base import Item, GradeResult

class HistoryGrader:
    subject_key = "history"
    def grade(self, answer: str, item: Item) -> GradeResult:
        # Offene Antwort: LLM darf nur einen VORSCHLAG machen (Rubric-gestützt).
        # Konfidenz strukturell < 1.0 -> wird ohne Lehrer-Bestätigung nicht zementiert (P6).
        # PII: Aufruf NUR über its.llm.client.complete (scrub vor externem Call, P4) — erst ab AG-3.
        return GradeResult(correct=False,
                           feedback="Vorläufige Einschätzung — wartet auf Lehrer-Review.",
                           confidence=0.5)
```

> Hinweis: zu entscheiden — der konkrete Confidence-Wert für History-Vorschläge (hier `0.5`) und die genaue LLM-Aufruf-Signatur hängen an AG-3 (`its.llm.client.complete`). Bis AG-3 existiert, bleibt `history.py` ein Stub **ohne** realen externen Call; entscheidend ist nur `confidence < 1.0` und der Review-Hinweis.

> Hinweis: zu entscheiden — das Language-Regelmodell (exakter String-Vergleich vs. Lemma/Vokabel-Set). Für das Grundgerüst genügt normalisierter Exaktvergleich; vertieftes NLP später.

Registrierung in `grading/__init__.py`:

```python
from its.grading.registry import register
from its.grading.language import LanguageGrader
from its.grading.history import HistoryGrader
register(LanguageGrader())
register(HistoryGrader())
```

## Umsetzungsschritte

- [ ] `language.py` mit `LanguageGrader` (`subject_key = "language"`) anlegen; deterministischer, normalisierter Vergleich gegen `item.answer_key`; `confidence = 1.0` bei klarem Ergebnis.
- [ ] `history.py` mit `HistoryGrader` (`subject_key = "history"`) anlegen; nutzt `item.rubric`; setzt `confidence < 1.0`; Feedback signalisiert Lehrer-Review; **kein** realer externer LLM-Call bevor AG-3 existiert (P4).
- [ ] In `grading/__init__.py` `register(LanguageGrader())` und `register(HistoryGrader())` ergänzen.
- [ ] Sicherstellen, dass History nie ein endgültiges „korrekt/falsch" mit hoher Konfidenz ohne menschliche Bestätigung produziert (P6).
- [ ] Tests `test_language.py` und `test_history.py` schreiben (siehe unten).
- [ ] `uv run ruff check src/its/grading/language.py src/its/grading/history.py` ausführen.

## Akzeptanzkriterien

- [ ] Language- und History-Grundgerüst vorhanden; History mit Lehrer-Override-Pfad (docs/06 AK: „Language/History-Grundgerüst; History mit Lehrer-Override-Pfad (GR-3)").
- [ ] `LanguageGrader` ist regelbasiert/deterministisch; bei eindeutigem Vergleich `confidence = 1.0`.
- [ ] `HistoryGrader` liefert für offene Antworten stets `confidence < 1.0` und einen Review-Hinweis (P6).
- [ ] History führt **keinen** rohen Schüler-Antworttext an eine externe API (P4); externer Pfad nur über den anonymisierenden Client (AG-3).
- [ ] Beide Grader sind über `get_grader("language")` bzw. `get_grader("history")` auffindbar.
- [ ] Nur `grading/` ist Plugin-Registry; keine eigene Mechanik (P7).

## Tests / Verifikation

```bash
cd apps/api
uv run pytest tests/test_grading/test_language.py tests/test_grading/test_history.py -q
```

Erwartet: alle Tests grün. Mindestfälle:

```python
# test_language.py
from its.grading.language import LanguageGrader
from its.grading.base import Item

def test_language_exact_match_accepted():
    g = LanguageGrader()
    item = Item(skill_key="vocab", prompt="Plural von 'Haus'", answer_key="Häuser")
    assert g.grade("  häuser ", item).correct is True
    assert g.grade("häuser", item).confidence == 1.0

def test_language_mismatch_rejected():
    g = LanguageGrader()
    item = Item(skill_key="vocab", prompt="Plural von 'Haus'", answer_key="Häuser")
    assert g.grade("Hausen", item).correct is False
```

```python
# test_history.py
from its.grading.history import HistoryGrader
from its.grading.base import Item

def test_history_is_never_high_confidence():
    g = HistoryGrader()
    item = Item(skill_key="ww1-causes", prompt="Nenne zwei Ursachen",
                answer_key="", rubric="Bündnissystem, Wettrüsten, Nationalismus")
    res = g.grade("Bündnisse und Nationalismus", item)
    assert res.confidence < 1.0           # P6: wird nicht ohne Review zementiert
```

Registrierungs-Check:
```python
from its.grading.registry import get_grader
import its.grading
assert get_grader("language").subject_key == "language"
assert get_grader("history").subject_key == "history"
```

Lint:
```bash
uv run ruff check src/its/grading/language.py src/its/grading/history.py   # erwartet: keine Fehler
```

## Abhaengigkeiten

- **GR-1** (`GraderStrategy`-Protokoll + Registry): GR-3 importiert die Typen aus `base.py` und registriert beide Grader über `register`.
- **Lose verknüpft / später**: **AG-3** (LLM-Client + `anonymize.scrub`): History kann erst dann real einen LLM-Vorschlag erzeugen; bis dahin Stub mit `confidence < 1.0`.
- **Nachgelagert**: **AG-2** (`assess_node`) ruft Language/History über `get_grader(subject_key)` auf; **AG-2/update_model_node** respektiert die niedrige Konfidenz (zementiert nicht automatisch).

## Definition of Done

(projektweite DoD aus docs/00 Section 8, auf GR-3 zugeschnitten)

- [ ] Akzeptanzkriterien aus docs/06 (GR-3) erfüllt — Language regelbasiert, History mit Lehrer-Override-Pfad und niedriger Konfidenz.
- [ ] Tests grün (`tests/test_grading/test_language.py`, `tests/test_grading/test_history.py`).
- [ ] Keine PII in externen LLM-Prompts: History führt vor AG-3 keinen externen Call; danach nur über den `scrub`-vorgeschalteten Client (P4).
- [ ] `uv`-only, keine `pip`-Aufrufe.
- [ ] Zugehöriges GitHub-Issue geschlossen, E7-Epic-Checkliste aktualisiert.
