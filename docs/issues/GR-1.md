## Ziel

Die strukturelle **Plugin-Naht** des Systems steht: ein `GraderStrategy`-Protokoll mit den Datentypen `Item` und `GradeResult` sowie eine fachgekeyte Registry. Am Ende kann ein Grader unter seinem `subject_key` registriert und über `get_grader(subject_key)` abgerufen werden — die Basis, auf der GR-2 (Math) und GR-3 (Language/History) aufsetzen.

## Kontext & Prinzipien

- **P7 — Genau eine Plugin-Naht (fachspezifische Bewertung)**: `GraderStrategy`, gekeyt auf das Fach, ist der **einzige** Strategy/Adapter-Punkt im gesamten System. Diese Task etabliert genau diese Naht. Begründung laut docs/00: erweiterbar durch Dritte, strukturell ähnliche aber inhaltlich diverse Fälle, separate Versionierung denkbar. Konkret hier: Es darf **keine** zweite Registry-/Plugin-Mechanik in `retrieval/`, `agent/` oder `learner_model/` entstehen — diese bleiben flache Module.
- **P2 — Kuratierte Antworten**: Die `Item`-Dataclass trägt einen `answer_key`, der **kuratiert** ist und niemals vom LLM erzeugt wird. Das Protokoll macht das strukturell sichtbar (Pflichtfeld, frozen).
- **P9 — `uv` ausschliesslich**: keine `pip`-Aufrufe; falls Tooling nötig, `uv add --dev`.

## Zu erstellende/aendernde Dateien

Gemäss Repository-Layout (docs/00, Section 6: `grading/  # base.py + registry.py + math/language/history  ← Plugin-Naht`):

- `apps/api/src/its/grading/__init__.py` — (neu) leer bzw. später Registrierungs-Ort.
- `apps/api/src/its/grading/base.py` — (neu) `Item`, `GradeResult`, `GraderStrategy`.
- `apps/api/src/its/grading/registry.py` — (neu) `register`, `get_grader`, `_REGISTRY`.
- `apps/api/tests/test_grading/__init__.py` und `apps/api/tests/test_grading/test_registry.py` — (neu) Registry-Roundtrip-Test.

> Hinweis: zu entscheiden — ob das Tests-Verzeichnis unter `apps/api/tests/` oder dem Repo-Root-`tests/` liegt. docs/00 Section 6 zeigt ein Root-`tests/`, docs/10 nutzt `tests/...` mit `working-directory: apps/api`. Empfehlung: `apps/api/tests/` (passt zum CI-`working-directory` und zu `uv run pytest` aus `apps/api`).

## Schnittstellen & Signaturen

`apps/api/src/its/grading/base.py` (exakt aus docs/06, Teil B.1):

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

`apps/api/src/its/grading/registry.py` (exakt aus docs/06, Teil B.1):

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

Downstream-Nutzung (docs/07, `assess_node`), zur Orientierung — **nicht** Teil dieser Task:

```python
from its.grading.registry import get_grader
from its.grading.base import Item
grader = get_grader(state.subject_key)
result = grader.grade(state.answer, item)
```

## Umsetzungsschritte

- [ ] Verzeichnis `apps/api/src/its/grading/` anlegen, `__init__.py` (zunächst leer) erstellen.
- [ ] `base.py` mit `Item`, `GradeResult` (beide `@dataclass(frozen=True)`) und `GraderStrategy` (`typing.Protocol`) exakt nach Spezifikation anlegen.
- [ ] `registry.py` mit modul-lokalem `_REGISTRY`, `register(grader)` und `get_grader(subject_key)` anlegen; `get_grader` wirft `LookupError` (nicht `KeyError`) bei unbekanntem Fach.
- [ ] Sicherstellen, dass `from its.grading.base import GraderStrategy, Item, GradeResult` und `from its.grading.registry import register, get_grader` importierbar sind (Package-Init vorhanden).
- [ ] Prüfen, dass kein generischer Registry-Helfer exportiert wird, der andere Module zur Pluginisierung verleitet (P7 schützen).
- [ ] Test-Verzeichnis `tests/test_grading/` mit `__init__.py` anlegen; `test_registry.py` schreiben (Roundtrip + `LookupError`).
- [ ] `uv run ruff check src/its/grading` ausführen und Lint-Fehler beheben.

## Akzeptanzkriterien

- [ ] `GraderStrategy`-Protokoll mit `subject_key: str` und `grade(self, answer: str, item: Item) -> GradeResult` vorhanden (docs/06 AK: „`GraderStrategy`-Protokoll + Registry, gekeyt auf Fach (GR-1)").
- [ ] `Item` trägt `skill_key`, `prompt`, kuratierten `answer_key` (Pflicht) und optionale `rubric`; `GradeResult` trägt `correct`, `feedback`, `confidence`.
- [ ] Registry `register`/`get_grader` keyt auf `subject_key`; `get_grader` auf unbekanntes Fach wirft `LookupError`.
- [ ] Nur `grading/` ist Plugin-Registry; keine analoge Mechanik in `retrieval/`/`agent/`/`learner_model/` (P7).
- [ ] `Item`/`GradeResult` sind unveränderlich (frozen) — der kuratierte `answer_key` kann im Bewertungspfad nicht mutiert werden (P2).

## Tests / Verifikation

```bash
cd apps/api
uv run pytest tests/test_grading/test_registry.py -q
```

Erwartet: alle Tests grün. Inhaltlich mindestens:

```python
from its.grading.registry import register, get_grader
from its.grading.base import Item, GradeResult

class _Dummy:
    subject_key = "dummy"
    def grade(self, answer, item):
        return GradeResult(True, "ok", 1.0)

def test_register_and_get_roundtrip():
    register(_Dummy())
    g = get_grader("dummy")
    assert g.subject_key == "dummy"
    assert g.grade("x", Item("s", "p", "x")).correct is True

def test_unknown_subject_raises_lookup_error():
    import pytest
    with pytest.raises(LookupError):
        get_grader("does-not-exist")
```

Zusätzlich:
```bash
uv run ruff check src/its/grading   # erwartet: keine Fehler
```

## Abhaengigkeiten

- **FND-2** (uv-Projekt initialisiert): liefert das lauffähige `apps/api`-Python-Projekt mit `uv`, in dem das `grading`-Package und die Tests laufen.
- **Nachgelagert** (warten auf GR-1):
  - **GR-2** (Math-Grader) importiert `GraderStrategy`/`Item`/`GradeResult` aus `base.py` und registriert sich.
  - **GR-3** (Language/History) ebenso.
  - **AG-1/AG-2** (Agent-Loop) nutzen `get_grader(subject_key)` in `assess_node` (docs/07).
  - **TST-2** testet Grader über dieses Protokoll.

## Definition of Done

(projektweite DoD aus docs/00 Section 8, auf GR-1 zugeschnitten)

- [ ] Akzeptanzkriterien aus docs/06 (GR-1) erfüllt.
- [ ] Tests grün (`tests/test_grading/test_registry.py`); keine Safety-Tests direkt betroffen (reine Logik, keine DB/PII).
- [ ] Keine PII in externen LLM-Prompts — n/a für GR-1 (kein LLM-Call).
- [ ] `uv`-only, keine `pip`-Aufrufe.
- [ ] Zugehöriges GitHub-Issue geschlossen, E7-Epic-Checkliste aktualisiert.
