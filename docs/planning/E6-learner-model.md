# E6 — Learner-Modell (BKT) — Detailplanung

## 1. Scope & Zielbild

Epic E6 baut das **Learner-Modell** — die zweite der vier ITS-Kernkomponenten (Domain / Learner / Pädagogik / Open Learner Model). Konkret entsteht eine **interpretierbare, inspizierbare Mastery-Schätzung pro (Schüler:in, Skill)** auf Basis von **Bayesian Knowledge Tracing (BKT)**.

Drei Bausteine:
1. **LM-1 — BKT-Kern**: Reine NumPy-/Python-Funktionen (`posterior`, `update`, `mastery_after`) plus `BKTParams`-Dataclass. Keine DB, keine Seiteneffekte — testbar als pure Logik.
2. **LM-2 — Tracing-Service**: `record_attempt(session, student_id, skill_id, correct, params)` — der **einzige** legitime Schreibpfad in die Tabelle `learner_state`. Hält `mastery`, `uncertainty` und `attempts_count` konsistent.
3. **LM-3 — DKT-Platzhalter**: Interface-kompatibler Stub `dkt.py` plus Aktivierungs-Doku — kein neuronales Modell, sondern die dokumentierte Naht für einen späteren Swap.

Zielbild am Epic-Ende: Eine Schülerantwort (boolean korrekt/falsch) kann über `record_attempt` deterministisch und auditierbar in eine aktualisierte Mastery + Unsicherheit überführt werden; diese Werte sind später vom Lehrer-Dashboard (Open Learner Model, P5) lesbar und überschreibbar (P6). Das **Modell** verbessert sich, nicht der Agent (P3).

**Was NICHT zu E6 gehört:** Grading (E7, P7-Plugin-Naht), Agent-Loop-Verdrahtung (E8 / `update_model`-Node), API-Endpunkte (E10), Dashboard (E11). E6 liefert die Bibliotheks-/Service-Schicht, die diese konsumieren.

## 2. Task-Reihenfolge & Abhängigkeiten

```
FND-2 (uv-Projekt, pyproject mit numpy)
   │
   ▼
LM-1 (bkt.py — pure Funktionen)
   │            DB-2 (db/models.py: LearnerState, Attempt)
   │             │
   ▼             ▼
LM-2 (tracing.py — record_attempt schreibt learner_state)
   │
   ▼
LM-3 (dkt.py — interface-kompatibler Stub + Doku)
```

Reihenfolge ist strikt linear:
- **LM-1** hängt nur von FND-2 (numpy in `pyproject.toml`).
- **LM-2** braucht LM-1 (`update`, `BKTParams`) **und** DB-2 (das ORM-Modell `LearnerState`).
- **LM-3** lehnt sich an LM-2 an (gleiche Service-Signatur als „interface-kompatibel").

Nachgelagert (außerhalb E6, hängen von E6 ab):
- **LM-2** wird von **AG-2** (`agent/nodes/update_model.py`) konsumiert (docs/07).
- **LM-1/LM-2** werden von **TST-2/TST-3** getestet (docs/10).
- Mastery/Unsicherheit werden vom **Lehrer-Dashboard (E11)** und der **Schüler-Mastery-Anzeige (E10)** gelesen.

## 3. Feinere Sub-Task-Zerlegung (über die Issues hinaus)

**LM-1**
- (a) `BKTParams` als `@dataclass(frozen=True)` mit Defaults (`p_init=0.2`, `p_learn=0.15`, `p_slip=0.10`, `p_guess=0.20`).
- (b) `posterior(p_known, correct, p)` — Bayes-Schritt, mit Division-durch-0-Schutz (`return ... if den > 0 else p_known`).
- (c) `update(p_known, correct, p)` — Posterior + Lern-Transition.
- (d) `mastery_after(sequence, p)` — Faltung über eine Sequenz, Start bei `p_init`.
- (e) Modul-Docstring + Typannotationen; bewusst KEINE DB-/IO-Importe (Reinheit).
- (f) Tests: Range, Monotonie, Vergleich falsch<richtig.

**LM-2**
- (a) `record_attempt`-Signatur exakt wie Doc.
- (b) Lookup über zusammengesetzten PK `(student_id, skill_id)` via `session.get(LearnerState, {...})`.
- (c) Erstanlage-Pfad: neuer `LearnerState` mit `mastery=p.p_init`, `uncertainty=1.0`, `attempts_count=0`, dann `session.add`.
- (d) Update-Pfad: `mastery = update(...)`, `attempts_count += 1`, `uncertainty = 1/(attempts_count+1)`.
- (e) Reihenfolge bewusst: erst Mastery aus altem Zustand rechnen, dann Zähler erhöhen, dann Unsicherheit neu setzen.
- (f) `updated_at` wird DB-seitig per `server_default=func.now()` gesetzt — entscheiden, ob beim Update explizit angefasst werden muss.
- (g) Service committet **nicht** selbst — Transaktionssteuerung beim Aufrufer (passt zu `scoped_session`, docs/03).
- (h) Integrationstest gegen Test-DB (transaktional, docs/10).

**LM-3**
- (a) Stub-Funktion/-Klasse mit derselben Aufruf-Form wie der Tracing-Service (interface-kompatibel).
- (b) `raise NotImplementedError(...)` mit klarer Begründung, ODER reine Doku-Datei mit Signatur-Skizze.
- (c) Aktivierungs-Doku: „erst wenn (1) genügend Interaktionshistorie vorliegt UND (2) BKT messbar limitiert ist" (P2/P5).
- (d) Notiz: DKT ist nicht interpretierbar → P5-Vorrang von BKT dokumentieren.

## 4. Zentrale Designentscheidungen (mit Begründung)

- **BKT statt DKT zuerst** (Tech-Stack-Tabelle docs/00 §5, P5): interpretierbar, funktioniert mit dünnen Daten, kein Trainingskorpus. Eine Lehrperson muss *warum* nachvollziehen können.
- **Pure Funktionen für die Mathematik (LM-1), Service für die Persistenz (LM-2)**: trennt testbare Logik von Seiteneffekten. Unit-Tests brauchen keine DB (docs/10 §1).
- **Genau ein Schreibpfad in `learner_state`** (Doc-Hinweis Zeile 88-89, P3): „Schreibt immer über diesen Service" → Mastery und Unsicherheit bleiben konsistent; das Modell aktualisiert sich, nicht der Agent.
- **Flaches Modul, keine Plugin-Registry** (P7): `learner_model/` ist bewusst kein Strategy/Adapter-Punkt — die einzige Plugin-Naht im Projekt ist `grading/`. DKT ist ein späterer *Swap derselben einen* Implementierung, kein paralleler Plugin.
- **`uncertainty = 1/(attempts_count+1)`** als grobes Maß (Doc Zeile 63-64): bewusst einfach, gut genug fürs Open Learner Model; verfeinerbar später.
- **Kein Commit im Service**: passt zur `scoped_session`-Transaktionsklammer (docs/03 §5) und zum `update_model`-Node (docs/07), der selbst committet.

## 5. Risiken & Gegenmaßnahmen

- **Falscher Schreibpfad umgeht den Service** → Inkonsistenz von Mastery/Unsicherheit. *Gegenmaßnahme*: Service als einzigen dokumentierten Pfad markieren; Code-Review/lint-Notiz; RLS schützt nur Zeilensicht, nicht Konsistenz.
- **Numerische Instabilität** (Division durch 0, Werte außerhalb [0,1]) → falsche Pädagogik. *Gegenmaßnahme*: `den>0`-Guard im Doc; Property-Test „immer in [0,1]".
- **`session.get` mit Composite-PK als Dict** verhält sich je nach SQLAlchemy-Version subtil → Lookup schlägt fehl, doppelte Zeilen. *Gegenmaßnahme*: SQLAlchemy 2.0-Form testen; Integrationstest mit zweimaligem `record_attempt`.
- **PII-Leck unwahrscheinlich, aber prüfen** (P4): `learner_state` enthält IDs, keine Klartext-PII; kein externer LLM-Call in E6. *Gegenmaßnahme*: bewusst keine Namen/Freitext im Modell.
- **DKT-Stub wird versehentlich aktiviert** → nicht-interpretierbare Black-Box im Pfad für Minderjährige (P5-Verletzung). *Gegenmaßnahme*: Stub wirft `NotImplementedError`; Aktivierungskriterien explizit dokumentiert.

## 6. Offene Fragen / zu treffende Entscheidungen

1. **BKT-Referenzwerte für die „bekannte kurze Sequenz"** (Test LM-1): Der Doc fordert „bekannte Referenzwerte", nennt aber keine. Es muss ein konkreter Erwartungswert (z. B. `mastery_after([True], BKTParams())`) berechnet und als Konstante festgehalten werden.
2. **`updated_at` beim Update**: Server-Default greift nur bei INSERT. Muss `record_attempt` `updated_at` beim UPDATE explizit setzen (oder ein `onupdate=func.now()` ans Modell)? Modell-Definition in docs/03 hat kein `onupdate`.
3. **Per-Skill-BKT-Parameter**: `BKTParams` ist global-default. Sollen Parameter pro Skill kalibrierbar/persistiert sein? docs/06 lässt das offen.
4. **DKT-Stub-Form**: reine Doku-Datei vs. lauffähiger Stub mit `NotImplementedError`? Der Doc sagt „interface-kompatibler Stub" — die exakte Signatur (gleich wie `record_attempt`? oder ein eigenes Predict-Interface?) ist nicht spezifiziert.
5. **Clamping**: Sollen `mastery`/`uncertainty` defensiv auf [0,1] geklemmt werden, oder verlässt man sich auf die Mathematik? (Numerisch kann minimal über 1.0 driften.)

## 7. Test-/Verifikationsstrategie fürs Epic

- **LM-1 (Unit, DB-frei, schnell)** — `tests/test_bkt.py` (docs/10 §4):
  - `posterior(...)` ∈ [0,1] für korrekt und falsch.
  - `mastery_after([True,True,True]) > mastery_after([True])` (Monotonie).
  - `mastery_after([False,False]) < mastery_after([True,True])`.
  - Zusatz: ein fixierter Referenzwert (siehe offene Frage 1).
- **LM-2 (Integration, Test-DB)** — neuer Test (z. B. `tests/test_tracing.py`): zweimal `record_attempt` auf demselben (student, skill); prüfen, dass `attempts_count == 2`, `mastery` gestiegen (bei korrekt), `uncertainty == 1/3`. Nutzt die transaktionale `db`-Fixture aus `conftest.py` (docs/10 §2).
- **LM-3** — Test/Assertion, dass der Stub eine `NotImplementedError` (oder dokumentiertes Äquivalent) wirft und die Aktivierungs-Doku vorhanden ist.
- Ausführung: `cd apps/api && uv run pytest tests/test_bkt.py -q` (Unit) und `uv run pytest tests/test_tracing.py -q` (Integration, benötigt laufendes Postgres via docker-compose).
- CI: läuft als Teil der vollen Suite (`uv run pytest -q`); die Safety-Tests bleiben der vorgelagerte blockierende Schritt (docs/10 §7).
