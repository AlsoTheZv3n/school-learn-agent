# E7 — Grading-Strategy-Registry (Plugin-Naht, P7) — Detailplanung

> Quelldokumente: `docs/06-learner-model-and-grading.md` (Teil B), `docs/00-architecture.md` (P1–P9, Section 6 Repo-Layout, Section 8 DoD). Milestone: **M3 Learning Engine**. Abhängig von **FND-2** (uv-Projekt steht).

## 1. Scope & Zielbild

E7 baut die **einzige Plugin-Naht** des gesamten Systems (P7): eine fachgekeyte `GraderStrategy`. Ziel ist, dass eine Schülerantwort gegen einen **kuratierten** Answer Key bewertet wird (P2) und ein `GradeResult(correct, feedback, confidence)` zurückkommt — deterministisch bei Mathe (`confidence=1.0`), mit Lehrer-Override-Pfad bei offenen Fächern (P6).

In Scope:
- `grading/base.py`: `Item`-Dataclass (mit kuratiertem `answer_key`), `GradeResult`-Dataclass, `GraderStrategy`-Protocol.
- `grading/registry.py`: `register()` / `get_grader()`, gekeyt auf `subject_key`.
- `grading/math.py`: symbolische/numerische Prüfung via SymPy, `confidence=1.0`.
- `grading/language.py`: regelbasiertes Grundgerüst, deterministisch wo möglich.
- `grading/history.py`: offene Antwort, LLM nur als *Vorschlag* mit `confidence < 1.0` + Lehrer-Override.
- `grading/__init__.py`: Registrierung der Grader beim Import (Start).
- Unit-Tests unter `tests/test_grading/`.

Explizit **nicht** in Scope (anderswo verortet):
- Das Laden des `Item` aus kuratierten Inhalten (`its.content.items.load_item`) — wird in E8/agent (`assess_node`) referenziert, ist aber nirgends spezifiziert (siehe offene Fragen).
- Das Schreiben ins `learner_state` / die Zementierungs-Logik (`confidence >= 0.9`) — gehört zu LM-2 (Tracing) und AG-2 (`update_model_node`).
- Der LLM-Client selbst (`llm/client.py`, `scrub`) — gehört zu AG-3. History ruft ihn nur über das vorhandene Interface auf.

Architektur-Leitsatz (docs/00, Section 6): „Nur `grading/` ist eine Plugin-Registry. `retrieval/`, `agent/`, `learner_model/` sind flache Module." E7 muss diese Asymmetrie sauber etablieren, ohne andere Module pluginisierbar zu machen.

## 2. Task-Reihenfolge & Abhängigkeiten

```
FND-2  ──►  GR-1 (base.py Protocol + registry.py)
                 │
                 ├──►  GR-2 (math.py, sympy, confidence=1.0)        [priority:critical]
                 │
                 └──►  GR-3 (language.py + history.py Grundgerüst)

Downstream (warten auf GR-*):
GR-1  ──►  AG-1 (agent/state + graph)            — Grader-Registry wird im Loop gebraucht
GR-1  ──►  AG-2 (assess_node ruft get_grader)    — bewertet über die Registry
GR-2  ──►  TST-2 (Unit-Tests Grading, test_math) — testet Math-Grader gegen Key
```

- **GR-1** ist die Naht und muss zuerst stehen; GR-2 und GR-3 importieren ausschliesslich aus `base.py`/`registry.py`.
- **GR-2** und **GR-3** sind voneinander unabhängig und können parallel laufen.
- GR-2 ist `priority:critical`, weil der Math-Grader der einzige vollständig deterministische Pfad ist und die P2-Garantie (kuratiert, nicht halluziniert) hier konkret eingelöst wird.

## 3. Feinere Sub-Task-Zerlegung (über die Issues hinaus)

**GR-1**
- 3.1 Verzeichnis `apps/api/src/its/grading/` mit `__init__.py` anlegen.
- 3.2 `base.py`: `Item` (frozen dataclass), `GradeResult` (frozen dataclass), `GraderStrategy` (Protocol mit `subject_key: str` + `grade(...)`).
- 3.3 `registry.py`: modul-lokales `_REGISTRY: dict[str, GraderStrategy]`, `register`, `get_grader` (wirft `LookupError` bei fehlendem Fach).
- 3.4 Entscheiden, wo registriert wird: `grading/__init__.py` als Registrierungs-Ort (Doc-Empfehlung). GR-1 legt das leere `__init__.py` an; GR-2/GR-3 ergänzen ihre `register(...)`-Zeile.
- 3.5 Mini-Test: `register`/`get_grader` Roundtrip mit einem Dummy-Grader; `get_grader("unknown")` wirft `LookupError`.

**GR-2**
- 3.6 `math.py`: `MathGrader` mit `subject_key = "math"`.
- 3.7 `grade`: `sp.sympify(answer)` + `sp.sympify(item.answer_key)`, Äquivalenz via `sp.simplify(got - expected) == 0`.
- 3.8 Fehlerbehandlung: `sp.SympifyError`/`TypeError` → `GradeResult(False, "Konnte die Eingabe nicht als Term lesen.", 1.0)`.
- 3.9 Registrierung in `grading/__init__.py`: `register(MathGrader())`.
- 3.10 Tests: äquivalente Formen akzeptiert, falsche abgelehnt, `confidence == 1.0`, unparsbare Eingabe → `correct is False, confidence 1.0`.
- 3.11 Härtung gegen SymPy-Eingabe-Risiken (siehe Risiken/offene Fragen): Eingabe begrenzen, möglichst `sp.parse_expr` mit eingeschränkter Transformations-/Local-Dict-Konfiguration prüfen.

**GR-3**
- 3.12 `language.py`: `LanguageGrader` mit `subject_key = "language"`; regelbasierter Vergleich (Normalisierung: trim, lowercasing, Mehrfach-Whitespace), deterministisch → `confidence = 1.0` bei Treffer/klarem Nicht-Treffer.
- 3.13 `history.py`: `HistoryGrader` mit `subject_key = "history"`; nutzt `item.rubric`; LLM nur als *Vorschlag*; `confidence < 1.0`; Feedback signalisiert Lehrer-Review.
- 3.14 Registrierung beider in `grading/__init__.py`.
- 3.15 Tests: Language deterministische Fälle; History setzt `confidence < 1.0` und macht keine endgültige Zementierungs-Aussage.

## 4. Zentrale Designentscheidungen (mit Begründung)

- **Protocol statt ABC** (Doc-konform): `GraderStrategy` ist ein `typing.Protocol`. Strukturelles Typing erlaubt Drittanbieter-Grader ohne Vererbungszwang — passt zu P7 („erweiterbar durch Dritte").
- **Frozen Dataclasses** für `Item`/`GradeResult`: Immutabilität verhindert versehentliche Mutation des kuratierten `answer_key` im Bewertungspfad (P2).
- **`answer_key` ist Pflichtfeld, `rubric` optional**: spiegelt, dass deterministische Fächer (Mathe/Sprache) einen Key brauchen, offene Fächer (Geschichte) eine Rubric.
- **`confidence` als erstklassiges Feld**: `1.0` = deterministisch geprüft. Werte `< 1.0` steuern downstream (`update_model_node`, Schwelle `>= 0.9` in AG-2), ob ein Resultat automatisch zementiert wird oder zu Lehrer-Review geht (P6). E7 setzt nur den Wert, die Schwellenlogik lebt in AG-2/LM-2.
- **Registrierung beim Import in `grading/__init__.py`**: zentrale, auffindbare Stelle. Side-Effect beim Import ist hier akzeptabel und Doc-empfohlen; Alternative (explizites `bootstrap_graders()`) als offene Frage notiert.
- **Keine LLM-Generierung des Schlüssels** (P2, hart): Mathe/Language erzeugen nie einen Key; History darf den LLM nur als Vorschlagsgeber für eine offene Antwort nutzen, niemals zum Erfinden der „Wahrheit".
- **`grading/` bleibt die einzige Naht** (P7): Keine Registry-/Plugin-Mechanik in `learner_model/`, `agent/`, `retrieval/`. E7 darf keine generischen Registry-Helfer exportieren, die andere Module zur Pluginisierung verleiten.

## 5. Risiken & Gegenmassnahmen (Epic-Ebene)

- **SymPy-Eingabe als Angriffsfläche**: `sympify` kann beliebigen Python-artigen Input evaluieren. Risiko bei minderjährigen Nutzern + offener Eingabe. → Eingabelänge begrenzen, `parse_expr` mit restriktivem `local_dict`/Transformationen prüfen, in Tests bösartige Eingaben abdecken.
- **Falsch-positive Mathe-Bewertung** (P2-Bruch): Numerische vs. symbolische Äquivalenz (z. B. `0.333` vs `1/3`) kann inkonsistent sein. → Klare Konvention im Code-Kommentar; Toleranz/Modus pro `Item` als offene Frage.
- **History zementiert versehentlich** (P6-Bruch): Wenn `confidence` zu hoch gesetzt wird, läuft ein LLM-Vorschlag ungeprüft ins `learner_state`. → History setzt strukturell `confidence < 1.0`; Test erzwingt das.
- **PII zum LLM** (P4-Bruch in History): Schülerantworten enthalten potenziell Namen. → History ruft ausschliesslich über den `scrub`-vorgeschalteten Client (AG-3); kein Roh-Antworttext direkt an externe APIs. Bis AG-3 existiert: History bleibt Stub ohne realen externen Call.
- **Plugin-Naht-Erosion** (P7-Bruch): Versuchung, andere Module ebenfalls „registrierbar" zu machen. → Code-Review-Checkpunkt + Doku, dass nur `grading/` Plugin ist.
- **`pip` statt `uv`** (P9): neue Dependency `sympy` ist bereits in `pyproject.toml` (FND-2) gelistet; falls weitere nötig, `uv add`. → DoD-Check.

## 6. Offene Fragen / zu treffende Entscheidungen

1. **`its.content.items.load_item` / `Item`-Quelle** ist in `assess_node` (docs/07) referenziert, aber nirgends spezifiziert. Wie kommt ein kuratiertes `Item` (inkl. `answer_key`) zur Laufzeit zustande? Empfehlung: aus dem kuratierten Vault/DB laden; E7 definiert nur die Dataclass, das Laden ist E5/E8-Sache — muss aber benannt werden.
2. **Numerische vs. symbolische Mathe-Äquivalenz**: Soll ein `Item` einen Modus/eine Toleranz tragen (z. B. `0.333 ≈ 1/3`)? Default symbolisch-exakt.
3. **`subject_key`-Vokabular**: Genaue Strings (`"math"`, `"language"`, `"history"`) müssen mit `TutorState.subject_key` und der `subjects`-Tabelle übereinstimmen.
4. **Registrierungs-Mechanismus**: Import-Side-Effect in `grading/__init__.py` vs. explizite `bootstrap_graders()`-Funktion (testbarer, kein Magic-Import). Empfehlung: Doc-konform Import-Side-Effect, plus optionale explizite Funktion.
5. **History-LLM-Schnittstelle**: Welche Funktion/Signatur (`its.llm.client.complete`) und welcher Confidence-Wert (z. B. `0.5`) für Vorschläge? Hängt an AG-3.
6. **Language-Regelmodell**: Welche Regeln genau (exakter String, Lemma-Vergleich, Vokabel-Set)? Für das Grundgerüst genügt normalisierter Exaktvergleich; vertieftes NLP später.

## 7. Test-/Verifikationsstrategie für das Epic

- **Ebene Unit (keine DB)**: Alle Grading-Tests sind reine Funktionstests (docs/10, Teststrategie-Pyramide), laufen schnell ohne Postgres.
- **Verzeichnis**: `tests/test_grading/` mit mindestens `test_math.py`; `test_registry.py`, `test_language.py`, `test_history.py` ergänzen.
- **Math (aus docs/10 §4 übernommen)**:
  - `Item(skill_key="expand", prompt="(x+1)^2", answer_key="x**2 + 2*x + 1")`; `grade("x^2+2*x+1", item).correct is True`.
  - `grade("x^2+1", item).correct is False and .confidence == 1.0`.
  - unparsbare Eingabe → `correct is False`, `confidence == 1.0`.
- **Registry**: `register`/`get_grader` Roundtrip; `get_grader("unknown")` → `LookupError`.
- **History**: jedes Resultat hat `confidence < 1.0`; kein automatisches „endgültig korrekt".
- **Ausführung**: `cd apps/api && uv run pytest tests/test_grading/ -q` → alle grün.
- **Lint**: `uv run ruff check src/its/grading` → keine Fehler.
- **P7-Check (manuell/Review)**: keine neue Registry/Plugin-Mechanik ausserhalb `grading/`.

