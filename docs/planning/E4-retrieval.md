# E4 — Retrieval: Router + 3 Modi + Graph — Detailplanung

> Milestone: **M2 Retrieval & Content**. Quelldokument: `docs/05-retrieval.md` (Abschnitte 1-5, 7).
> Begleitende Prinzipien aus `docs/00-architecture.md` (P1-P9), Repository-Layout (Section 6),
> Definition of Done (Section 8). Abhaengige Pakete: SAF-2/SAF-3 (`docs/04-safety.md`),
> DB-2 (`docs/03-database.md`), CON-2 (`docs/05-retrieval.md` Abschnitt 6.2).

## 1. Scope & Zielbild

E4 baut die **Retrieval-Schicht** des ITS: die Schicht zwischen dem paedagogischen Agenten
(E8) und der *einen* PostgreSQL-Datenbank. Sie realisiert das Kernversprechen der Architektur
("derselbe Datenbestand, drei Zugriffsmuster" — `docs/00` Section 3):

- **Router (RET-1):** entscheidet pro Anfrage den Modus (semantic/individual/population) und ob
  eine strukturierte Live-Query noetig ist; die Entscheidung wird mit `reason` geloggt (auditierbar, P6).
- **Semantic (RET-2):** skalenfreie, geteilte `pgvector`-Aehnlichkeitssuche ueber Lernmaterial.
  Kein Personenbezug, keine RLS noetig — das ist Content, kein personenbezogenes Datum.
- **Individual (RET-3, `safety-critical`):** immer auf genau **eine** `student_id` gescoped,
  doppelt abgesichert durch `require_student_scope` (SAF-2) **und** RLS.
- **Population (RET-4, `safety-critical`):** `GROUP BY`-Aggregate ausschliesslich durch
  `enforce_min_cohort` (SAF-3) — keine De-Anonymisierung ueber kleine Kohorten.
- **Graph (RET-5):** rekursive CTE ueber `skill_edges` (Voraussetzungen/verwandte Skills) mit
  Tiefenlimit gegen Zyklen.

Nicht in E4: Content-Ingestion/Parser (CON-1..3, gehoeren zu E5, liefern aber das Datenmaterial,
das RET-2/RET-5 abfragen), Agent-Verdrahtung (E8), Learner-Modell-Updates (E6), das HTTP-API (E9).

Am Ende von E4 existiert das flache Modul `apps/api/src/its/retrieval/` mit fuenf Implementierungen
(keine Plugin-Naht — P7: nur `grading/` ist pluginisiert), die der Agent in E8 ueber
`agent/nodes/retrieve.py` und `agent/nodes/route.py` aufruft.

## 2. Task-Reihenfolge & Abhaengigkeiten

```
Voraussetzungen (andere Epics, muessen fertig sein):
  SAF-2 (scoping.require_student_scope)  ─┐
  SAF-3 (cohort.enforce_min_cohort)      ─┤
  DB-2  (db/models.py: ContentEmbedding, ─┤
         ContentNote, LearnerState,      │
         SkillEdge, Skill, Enrollment)   │
  CON-2 (Ingestion fuellt content_*)     │   (nur fuer RET-2 End-to-End-Test)
                                         ▼
E4-interne Reihenfolge (weitgehend parallelisierbar):

  RET-1 (Router)  ◄── SAF-2, SAF-3   [reine Funktion, keine DB → zuerst, blockiert E8]
        │
        ▼ (Modus-Enum wird von Agent/Tests konsumiert)
  RET-3 (Individual) ◄── SAF-2        ┐
  RET-4 (Population) ◄── SAF-3        ├─ DB-getriebene Modi, unabhaengig voneinander
  RET-5 (Graph)      ◄── DB-2         ┘
  RET-2 (Semantic)   ◄── DB-2, CON-2  [braucht eingespielte Embeddings fuer echten Test]

Nachgelagert (warten auf E4):
  RET-1 → AG-2 (agent/nodes/route.py, docs/07) — Router-Aufruf
  RET-2/3/4 → AG-2 (agent/nodes/retrieve.py) — Modus-Aufruf
  RET-3/4 → E9 (api/student.py, api/teacher.py) — Endpunkte
  RET-5 → E6/E8 — "naechster Schritt"/Voraussetzungs-Logik
```

Empfohlene Bearbeitung: **RET-1 zuerst** (reine Funktion, schnell testbar, entblockt E8), danach
RET-3/RET-4/RET-5 parallel (alle benoetigen nur Seed-Daten aus DB-4), **RET-2 zuletzt** (braucht
echte Embeddings aus CON-2 fuer einen aussagekraeftigen Integrationstest; bis dahin Stub-Vektoren).

## 3. Feinere Sub-Task-Zerlegung (ueber die Issues hinaus)

**RET-1 Router**
- `Mode`-StrEnum + `RouteDecision`-Dataclass (frozen) exakt wie Doc.
- Regelwerk als geordnete Liste von (Praedikat → (Mode, escalate, reason)); erste Regel gewinnt.
- Schluesselwort-Listen (DE) als Modul-Konstanten: Aggregat-Begriffe, Personenbezugs-Begriffe,
  Eskalations-Trigger ("genau", "aktuell", "Zahl", "Durchschnitt").
- `has_student_scope=False` darf nie INDIVIDUAL zurueckgeben (Fallback SEMANTIC) — fail-safe.
- Strukturiertes Logging via `logging.getLogger("its.retrieval.router")` mit `extra={...}`.
- Unit-Tests fuer jeden Pfad inkl. Eskalations-Flag.

**RET-2 Semantic**
- `semantic_search(session, query_embedding, k)` exakt wie Doc (HNSW, `<=>`).
- Vektor-Bindung: `pgvector`-konformer Literal-String via `str(list[float])` (wie im Doc-Snippet).
- `k`-Parameter validieren (>0), Default 5.
- Rueckgabe: Liste `dict` mit `chunk`, `sidecar_query`, `skill_id`.
- Sub-Frage: Embedding des Querytexts — kommt aus dem LLM-Client (`docs/07`), nicht aus diesem
  Modul; RET-2 nimmt den Vektor entgegen, berechnet ihn nicht. (Siehe offene Fragen.)

**RET-3 Individual**
- `mastery_overview(session, principal)` exakt wie Doc.
- `require_student_scope` zuerst (fail-closed) → liefert `sid`; Query gegen `learner_state JOIN skills`.
- Rueckgabe inkl. `uncertainty` (P5, fuer Open Learner Model) und `attempts_count`.
- Defense-in-depth: Code-Filter `WHERE ls.student_id = :sid` **plus** RLS-Session.
- Test mit `db_factory.as_student(...)`: Schueler sieht nur eigene Zeilen; ungescopter Principal → `ScopeError`.

**RET-4 Population**
- `skill_mastery_distribution(session, class_id, skill_id)` exakt wie Doc.
- `count(*)` + `avg(mastery)` in **einer** Query; Ergebnis durch `enforce_min_cohort` schleusen.
- `avg_mastery` runden (3 Nachkommastellen) und in `payload` packen.
- `None`-Handling fuer leere Kohorte (`avg(...) or 0.0`).
- Test: n < k → `CohortTooSmall`; n >= k → `CohortResult` mit Payload.

**RET-5 Graph**
- `prerequisites(session, skill_id, max_depth=5)` exakt wie Doc (`WITH RECURSIVE`).
- Tiefenlimit `d.depth < :md` als Zyklus-/Tiefenschutz.
- `DISTINCT` + `min(depth)` + `ORDER BY depth`.
- Optional (Hinweis, nicht im Doc spezifiziert): zweite Funktion `related(...)` fuer `kind='related'`
  — siehe offene Fragen, vorerst nur `prerequisite`.
- Test mit Seed-Graph `linear-equations → complete-the-square → quadratic-formula` (DB-4).

**Querschnitt**
- `apps/api/src/its/retrieval/__init__.py` anlegen (Paket-Init), saubere Re-Exports optional.
- Keine neue Dependency noetig (alles via vorhandenem `sqlalchemy`, `pgvector`) → **kein `uv add`** erwartet.
- Type-Hints konsistent; `ruff` clean (line-length 100, py312).

## 4. Zentrale Designentscheidungen mit Begruendung

1. **Flaches Modul, keine Plugin-Naht (P7).** `retrieval/` enthaelt je eine Implementierung pro
   Modus — kein Strategy/Registry-Muster. Die einzige Plugin-Naht im Projekt ist `grading/`.
   Begruendung: "nur eine echte Implementierung" ist Gegenindikator fuer Pluginisierung.
2. **Sicherheit in der DB, nicht im Router (P1).** Der Router faellt eine *Routing*-Entscheidung,
   keine *Autorisierungs*-Entscheidung. Selbst wenn der Router faelschlich INDIVIDUAL waehlt,
   verhindert RLS fremde Zeilen; selbst bei POPULATION verhindert `enforce_min_cohort` die
   De-Anonymisierung. Der Router ist damit unkritisch fuer die Isolation.
3. **Doppelte Absicherung Individual (P1).** `require_student_scope` (App-Schicht, fail-closed)
   **und** RLS (DB-Schicht). Bewusste Redundanz: ein Code-Fehler in einer Schicht leakt keine
   Kinderdaten.
4. **Aggregate immer durch einen Engpass (SAF-3).** `skill_mastery_distribution` gibt sein
   Ergebnis ausschliesslich via `enforce_min_cohort` zurueck — es gibt keinen Codepfad, der ein
   rohes Aggregat zurueckgibt.
5. **Geteiltes Wissen ohne RLS (P-Modi).** `content_embeddings`/`content_notes` tragen keinen
   `student_id` und sind kein personenbezogenes Datum → RET-2 braucht keine gescopte Session.
6. **Code wird nicht mit-embeddet (E5-Kernregel).** RET-2 verlaesst sich darauf, dass CON-2 nur
   Prosa embeddet und SQL als `sidecar_query` getrennt haelt — sonst verzerren SQL-Tokens den Vektor.
7. **Regelbasierter Router zuerst.** Bewusst keine ML-Klassifikation am Start; `RouteDecision.reason`
   bleibt erhalten, falls spaeter ein Klassifikator folgt (auditierbar, P6).
8. **Tiefenlimit im Graph statt Zyklus-Erkennung.** Einfacher, ausreichend, solange die Graphtiefe
   gemessen unkritisch bleibt (keine separate Graph-DB — Tech-Stack-Entscheidung `docs/00` Section 5).

## 5. Risiken & Gegenmassnahmen (Epic-Ebene)

- **Router waehlt POPULATION fuer eine Ein-Personen-Frage.** → Min-Cohort faengt es ab; zusaetzlich
  Router-Tests pro Pfad.
- **RET-2 ohne eingespielte Embeddings (CON-2 noch nicht fertig).** → RET-2 zuletzt einplanen; bis
  dahin Integrationstest mit manuell eingefuegten Stub-Embeddings markieren/skippen.
- **Vektordimension-Drift (Platzhalter `vector(1024)`).** Embedding-Modell und Dimension sind noch
  nicht final (offene Frage). RET-2 ist dimensionsunabhaengig, der Test muss aber die reale Dimension
  treffen. → Dimension zentral aus DB-Schema/Settings ableiten, nicht hartcodieren.
- **SQL-Injection ueber Vektor-Literal.** `str(query_embedding)` wird per Bindparam uebergeben (kein
  String-Format in die Query) → sicher, solange `query_embedding` `list[float]` ist; Typ pruefen.
- **RLS nicht aktiv in der Test-DB.** → Tests laufen gegen echtes Postgres mit angewandtem
  `rls.sql` (Alembic upgrade head, siehe `docs/10`), nicht gegen SQLite.

## 6. Offene Fragen / zu treffende Entscheidungen

(Strukturiert ausgegeben in `open_questions`. Zusammengefasst:)
- Konkretes Embedding-Modell + reale Vektordimension (Platzhalter 1024).
- Wer berechnet das Query-Embedding fuer RET-2 (LLM-Client `docs/07` vs. eigene Funktion)?
- `load_item`/`content/items.py` (in `docs/07` referenziert) ist nirgends spezifiziert — betrifft
  zwar primaer E8, aber RET-2s `item_ref`-Bezug haengt davon ab.
- Soll RET-5 auch `kind='related'` traversieren oder nur `prerequisite`?
- Soft-Cohort via Vektor-Aehnlichkeit (im Doc erwaehnt) — Definition/Scope fuer dieses Epic?
- `teacher_id`-Session-Variable fuer RET-3 bei Lehrer-Zugriff (RET-3 nutzt nur student-scope).

## 7. Test-/Verifikationsstrategie fuer das Epic

- **Unit (keine DB):** Router-Pfade (RET-1) und `enforce_min_cohort`-Verhalten (ueber RET-4
  indirekt). Schnell, in jeder PR.
- **Integration (echtes Postgres mit RLS, Fixtures aus `docs/10` `conftest.py`):**
  - RET-3: `db_factory.as_student(a.id)` sieht nur eigene `learner_state`-Zeilen; ungescopter
    Principal → `ScopeError`.
  - RET-4: kleine Kohorte → `CohortTooSmall`; ausreichende Kohorte → Payload mit `avg_mastery`.
  - RET-5: Seed-Graph liefert erwartete Voraussetzungs-Tiefen.
  - RET-2: gegen eingespielte Demo-Embeddings (CON-3 Vault) Top-k-Treffer + `sidecar_query`.
- **CI:** alle Tests via `uv run pytest -q` in `apps/api`; Safety-relevante Tests (RET-3/RET-4)
  laufen gegen RLS-aktivierte DB. Keine `pip`-Aufrufe (P9).
- **Manuell:** `uv run python -c "..."` Smoke-Skripte gegen die Docker-DB fuer jede Funktion.
