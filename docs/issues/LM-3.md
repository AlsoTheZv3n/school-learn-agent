## Ziel

Ein interface-kompatibler **DKT-Platzhalter** (`dkt.py`): kein neuronales Modell, sondern ein dokumentierter Stub plus klare Aktivierungs-Doku. Er hält die Naht für einen späteren Swap von BKT auf Deep Knowledge Tracing offen, ohne ihn jetzt zu aktivieren.

## Kontext & Prinzipien

- **P5 — Open Learner Model (interpretierbar):** DKT ist neuronal und NICHT interpretierbar. Für Minderjährige hat BKT Vorrang, weil eine Lehrperson *warum* nachvollziehen können muss. Der Stub dokumentiert genau diesen Vorrang und darf nicht versehentlich aktiv werden.
- **P2 — Kuratiert vor generativ / vorsichtig erst bei Bedarf:** Der Doc schreibt vor, DKT „erst aktivieren, wenn genügend Interaktionshistorie vorliegt **und** BKT messbar limitiert" ist. Datengetriebene Modelle ohne ausreichende, saubere Historie würden Kinder falsch modellieren.
- **P7 — flaches Modul, ein Swap (kein Plugin):** `learner_model/` ist KEINE Plugin-Registry. DKT ist ein späterer Ersatz *derselben einen* Implementierung, nicht eine zweite registrierte Strategie. Der Stub darf keine Strategy/Registry einführen.
- **P9 — `uv` ausschliesslich.**

## Zu erstellende/ändernde Dateien

- `apps/api/src/its/learner_model/dkt.py` (neu) — interface-kompatibler Stub + Doku.

## Schnittstellen & Signaturen

Vorgabe aus docs/06 §A.3:

> `apps/api/src/its/learner_model/dkt.py`: interface-kompatibler Stub + Doku „erst aktivieren, wenn genügend Interaktionshistorie vorliegt **und** BKT messbar limitiert" (P2/P5).

Referenz, an der sich „interface-kompatibel" orientiert (aus LM-2, der bestehende Tracing-Schreibpfad):

```python
def record_attempt(session: Session, student_id, skill_id, correct: bool,
                   params: BKTParams | None = None) -> LearnerState:
    ...
```

Skizze des Stubs (an die LM-2-Signatur angelehnt, damit ein späterer Swap minimal-invasiv ist):

```python
"""DKT-Platzhalter (Deep Knowledge Tracing).

NICHT AKTIV. Bewusst ein Stub. Aktivieren erst, wenn BEIDE Bedingungen gelten:
  1) Es liegt genügend saubere Interaktionshistorie pro Schüler:in/Skill vor.
  2) BKT ist messbar limitiert (belegt durch Offline-Auswertung gegen gehaltene Daten).

Vorrang BKT (P5): DKT ist neuronal und NICHT interpretierbar. Für Minderjährige hat
die inspizierbare BKT-Schätzung Vorrang (Open Learner Model). Ein Swap auf DKT erfordert
einen expliziten, dokumentierten Architektur-Entscheid.
"""
from sqlalchemy.orm import Session


def record_attempt_dkt(session: Session, student_id, skill_id, correct: bool):
    raise NotImplementedError(
        "DKT ist ein Platzhalter. Aktivierung erst bei ausreichender Historie UND "
        "messbarer BKT-Limitierung (siehe Modul-Docstring, P2/P5)."
    )
```

> Hinweis: zu entscheiden — die exakte Form des „interface-kompatiblen Stubs" ist im Doc nicht festgelegt: (a) eine zu `record_attempt` formgleiche Funktion, die `NotImplementedError` wirft, oder (b) eine reine Doku-Datei mit Signatur-Skizze. Empfehlung im Body folgt der LM-2-Signatur (Variante a), damit der spätere Swap an einer Stelle greift.

## Umsetzungsschritte

- [ ] `apps/api/src/its/learner_model/dkt.py` anlegen.
- [ ] Modul-Docstring mit den **zwei** Aktivierungsbedingungen (genügend Historie UND BKT messbar limitiert) und der P5-Begründung (Interpretierbarkeit/Vorrang BKT) schreiben.
- [ ] Einen interface-kompatiblen Stub bereitstellen, der `NotImplementedError` mit klarer Meldung wirft (nicht still durchlaufen).
- [ ] Sicherstellen, dass der Stub NICHT versehentlich von Tracing/Agent importiert/aufgerufen wird (kein Verdrahten in `update_model`).
- [ ] Keine Plugin-/Registry-Struktur einführen (P7) — flache Datei.
- [ ] Kurzer Test/Assertion, dass der Aufruf `NotImplementedError` wirft (Schutz gegen versehentliche Aktivierung).
- [ ] `uv run ruff check` grün.

## Akzeptanzkriterien

- [ ] `dkt.py` existiert als interface-kompatibler Stub (Aufrufform an LM-2 angelehnt).
- [ ] Aktivierungs-Doku ist vorhanden und nennt BEIDE Bedingungen (genügend Historie UND messbar limitiertes BKT) sowie den P5-Vorrang von BKT.
- [ ] Der Stub ist nicht funktional aktiv (wirft `NotImplementedError` oder dokumentiertes Äquivalent) — keine stille Black-Box im Pfad.
- [ ] `learner_model/` bleibt ein flaches Modul ohne Plugin-Registry (P7).

## Tests / Verifikation

```bash
cd apps/api
uv run python -c "from its.learner_model import dkt; print('import ok')"
uv run pytest tests/test_dkt_stub.py -q   # falls Test angelegt
```

Erwartet: Import funktioniert; der Aufruf des Stubs wirft `NotImplementedError`. Beispiel:

```python
import pytest
def test_dkt_stub_not_active():
    from its.learner_model.dkt import record_attempt_dkt
    with pytest.raises(NotImplementedError):
        record_attempt_dkt(None, None, None, True)
```

## Abhängigkeiten

- **LM-2** — liefert das Referenz-Interface (`record_attempt`), an dem sich „interface-kompatibel" orientiert; ohne den etablierten Tracing-Schreibpfad gibt es keine Form, mit der der Stub kompatibel sein soll.
- Nachgelagert: ein künftiges DKT-Aktivierungs-Epic (nicht Teil von M3) würde diesen Stub durch eine echte Implementierung ersetzen.

## Definition of Done

- [ ] Akzeptanzkriterien dieses Tasks erfüllt (Stub interface-kompatibel + Aktivierungs-Doku).
- [ ] Tests grün (Import + `NotImplementedError`-Test); keine Safety-Tests betroffen.
- [ ] Keine PII in externen LLM-Prompts — N/A.
- [ ] `uv`-only, keine `pip`-Aufrufe.
- [ ] Zugehöriges GitHub-Issue (LM-3) geschlossen, Epic-Checkliste E6 aktualisiert.
