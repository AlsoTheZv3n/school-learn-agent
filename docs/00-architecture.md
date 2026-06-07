# 00 — Architektur & Kernprinzipien

> **Dies ist das wichtigste Dokument.** Es definiert die Constraints, an die sich jedes
> Arbeitspaket halten muss. Wenn ein späteres Dokument im Widerspruch zu hier steht, gilt
> dieses Dokument.

---

## 1. Was wir bauen

Ein **Intelligent Tutoring System (ITS)** nach dem klassischen Vier-Komponenten-Modell:

1. **Domain-Modell** — das Lernmaterial pro Fach/Stufe (kuratiert).
2. **Learner-Modell** — der individuelle Wissensstand pro Schüler:in (Knowledge Tracing).
3. **Pädagogisches Modell** — der Agent, der erklärt, abfragt und den nächsten Schritt wählt.
4. **Open Learner Model + Lehreraufsicht** — eine Ansicht, in der eine echte Lehrperson den
   Stand einsehen, verifizieren und eingreifen kann.

Diese vier sitzen auf einer **Drei-Modus-Retrieval-Schicht** über **einer** Datenbank, und
alles läuft durch ein **Safety-/Isolations-Gate**.

---

## 2. Architekturdiagramm (textuell)

```
                 Schüler:in
                     ↕            (Dialog: lehren ⇄ antworten)
            Pädagogischer Agent  ────────────────┐
                     ↕            (liest/schreibt) │ (Intervention, gestrichelt)
              Learner-Modell  ⇄  Lehrer-Dashboard ─┘   (Open Learner Model)
                     ↓            (fragt Wissen ab)
              Retrieval-Router
            ┌────────┼────────┐
        Semantic  Individual  Population
       (geteilt) (1 student) (Kohorte)
            └────────┼────────┘
        ╔════════════▼════════════╗
        ║   Safety & Isolation    ║   row-level scoping · min-cohort threshold
        ╚════════════▼════════════╝
            ┌────────────────┐
        Vector store      Structured DB
        (Lernmaterial)    (pro Schüler)
```

**Lesart:** Anfragen fliessen abwärts (Agent → Router → Modi → Daten), Resultate aufwärts.
Das Gate filtert in **beide** Richtungen: Scoping auf dem Hinweg, Min-Cohort auf dem Rückweg.

---

## 3. Die drei Retrieval-Modi

Wissen skaliert unterschiedlich — derselbe Datenbestand, drei Zugriffsmuster:

| Modus | Scope | Quelle | Beispiel-Frage |
|---|---|---|---|
| **Semantic** | skalenfrei, geteilt | `pgvector` über Lernmaterial | „Was bedeutet quadratische Ergänzung?" |
| **Individual** | genau 1 `student_id` | relationale Query (RLS-geschützt) | „Wo steht *dieser* Schüler?" |
| **Population** | Kohorte (n ≥ k) | `GROUP BY`-Aggregat (Min-Cohort) | „Wie steht die Klasse zu diesem Thema?" |

Erklärendes/semantisches Wissen ist identisch für eine:n oder eine Million Lernende → einmal
ablegen, geteilt nutzen. Niemals pro Schüler:in duplizieren.

---

## 4. Nicht verhandelbare Prinzipien

Diese gelten projektweit. Jedes Arbeitspaket respektiert sie.

### P1 — Safety zuerst, in der Datenbank verankert
Die Isolation (eine:r sieht nur eigene Zeilen) wird über **Postgres Row-Level Security**
erzwungen, nicht über `if`-Checks im Anwendungscode. Selbst eine fehlerhafte Query darf
keine fremden Zeilen zurückgeben. **Dieses Paket wird früh gebaut** (Milestone M1), bevor
Features darauf aufsetzen, die seine Existenz voraussetzen.

### P2 — Kuratierte Antworten, generative Freiheit nur wo Fehler sichtbar sind
Der **Bewertungs-/Antwortpfad** (`assess`) stützt sich auf einen **kuratierten Answer Key**,
nicht auf freie LLM-Generierung. Ein LLM, das den richtigen Antwortschlüssel halluziniert,
würde ein Kind falsch unterrichten. Generative Freiheit ist auf **Erklärung/Umformulierung**
(`explain`) beschränkt — dort sind Fehler geringfügig und sofort sichtbar (das Kind fragt
einfach erneut).

### P3 — Das Learner-Modell „verbessert sich", nicht der Agent
Es ist verlockend, einen Agenten „sich selbst verbessern" zu lassen. Stattdessen: das
**Learner-Modell** (eine inspizierbare Mastery-Schätzung pro Skill) wird aktualisiert, und
das Verhalten des Agenten ist eine (weitgehend deterministische) Funktion dieses Modells.
Das System wird besser darin, **die Lernenden zu modellieren** — der Agent mutiert nicht
selbst. Das macht Verhalten auditierbar (P7).

### P4 — PII verlässt die Maschine nicht im Klartext
Es geht um Minderjährige. Vor jedem Prompt, der an eine externe API geht, wird **PII
entfernt** (`llm/anonymize.py`). Der Agent erhält Skill-IDs und anonymisierten Kontext —
nicht „Sven, 14, hat Mühe mit …". Alternativ läuft alles Identifizierende auf einem lokalen
Modell.

### P5 — Open Learner Model (für Menschen inspizierbar)
Das Learner-Modell muss von einer Lehrperson **einsehbar** sein — inkl. seiner Unsicherheit —
nicht eine Black-Box, der man blind vertrauen muss. Deshalb BKT (interpretierbar) vor DKT
(neuronal). Die Lehrperson kann sehen **warum** das System ein Kind als „nicht gemeistert"
einschätzt und das überschreiben.

### P6 — Mensch im Loop ist Sicherheitsarchitektur, kein Reporting
Die Fähigkeit der Lehrperson zu **verifizieren und einzugreifen** ist ein erstklassiger Pfad,
kein Admin-Nachgedanke. Eine KI ist nicht die alleinige Instanz über den Lernweg eines Kindes.

### P7 — Genau **eine** Plugin-Naht: fachspezifische Bewertung
`GraderStrategy`, gekeyt auf das Fach (Mathe = symbolisch/numerisch, Sprache = andere Logik,
Geschichte = offene Antwort), ist der **einzige** Strategy/Adapter-Punkt. Begründung: erweiterbar
durch Dritte, strukturell ähnliche aber inhaltlich diverse Fälle, separate Versionierung denkbar.
**Alles andere** (Tracing-Loop, Router, Dashboard) bleibt **eine** Implementierung — Gegenindikator
ist „nur eine echte Implementierung". Nicht pluginisieren.

### P8 — Datenresidenz CH/EU
Schülerdaten Minderjähriger ⇒ CH/EU-Residenz (revDSG/DSGVO). Railway o. Ä. nur für Prototyp;
Produktion in CH/EU-Region (z. B. Azure Switzerland, Exoscale, Infomaniak).

### P9 — `uv` ausschliesslich
Im Python-Teil wird **`uv`** für alles verwendet (Dependencies, venv, Ausführung). **Kein `pip`.**

---

## 5. Tech-Stack (mit Begründung)

| Teil | Wahl | Warum |
|---|---|---|
| Datenbank | **PostgreSQL + `pgvector`** | Drei Modi aus *einer* DB: Embeddings, relationale Daten, Aggregate. Keine separate Vektor-/Graph-DB. |
| Link-Graph | `edges`-Tabelle + rekursive CTE | Obsidian-Links sind getypte Kanten; Graph quasi gratis. Echte Graph-DB erst bei gemessenem Engpass. |
| Isolation | **RLS** + Min-Cohort-Check | Die gefährliche Hälfte (Zeilenisolation) wird Schema-Eigenschaft statt Code-Disziplin. |
| Agent/Router | **LangGraph** | Expliziter State-Graph = auditierbares Routing (P7/P6). |
| Lernmodell | **BKT** (NumPy) | Interpretierbar (P5), funktioniert mit dünnen Daten, kein Trainingskorpus nötig. DKT als späterer Swap. |
| LLM | Frontier-API (anonymisiert) **oder** lokal Qwen2.5 | Qualität für Erklärungen; Compliance bestimmt den Ort der Inferenz (P4/P8). |
| Backend | **FastAPI** + Pydantic | Pydantic validiert Query-Parameter für sichere Templates. |
| Frontend | **React + TypeScript** | Eine Skill, zwei sehr unterschiedliche Sichten (Schüler ruhig / Lehrer dicht). |
| Auth | **Keycloak/Authentik** o. **Entra ID** | Rollentrennung student/teacher/admin — genau die Rollen, auf die RLS keyt. |
| Hosting | **CH/EU-Region** | P8. |

---

## 6. Repository-Layout (Ziel)

```
its-platform/
├── apps/
│   ├── api/                # FastAPI (uv)
│   │   └── src/its/
│   │       ├── db/         # models, session, migrations
│   │       ├── safety/     # rls.sql, cohort.py, scoping.py   ← M1, zuerst
│   │       ├── retrieval/  # router, semantic, individual, population, graph
│   │       ├── agent/      # LangGraph: graph.py, state.py, nodes/
│   │       ├── learner_model/  # bkt.py, tracing.py, dkt.py (Platzhalter)
│   │       ├── grading/    # base.py + registry.py + math/language/history  ← Plugin-Naht
│   │       ├── content/    # parser.py (Prosa/Code-Split), ingest.py
│   │       ├── llm/        # client.py, anonymize.py, prompts/
│   │       ├── auth/       # roles.py, deps.py
│   │       └── api/        # student.py, teacher.py
│   └── web/                # React + TS (student/ + teacher/)
├── content/               # kuratierter Markdown-Vault (Prosa + ```sql-Blöcke)
├── infra/                 # docker-compose, deploy
├── tests/                 # inkl. test_rls.py, test_cohort_threshold.py (CI-blockierend)
└── README.md
```

> Die Asymmetrie ist beabsichtigt: nur `grading/` ist eine Plugin-Registry (P7). `retrieval/`,
> `agent/`, `learner_model/` sind flache Module — je eine Implementierung.

---

## 7. Glossar

- **BKT** — Bayesian Knowledge Tracing: pro Skill vier Wahrscheinlichkeiten (prior, learn, slip, guess).
- **DKT** — Deep Knowledge Tracing: neuronale (LSTM-)Variante; später, datengetrieben.
- **Open Learner Model** — für die Lehrperson einsehbarer Lernstand inkl. Unsicherheit.
- **RLS** — Row-Level Security: Postgres erzwingt Zeilen-Sichtbarkeit per Policy/Rolle.
- **Min-Cohort-Schwelle (`k`)** — Aggregate werden verweigert, wenn die Gruppe < `k` Personen umfasst.
- **PII** — personenbezogene Daten (Name, Geburtsdatum, …).

---

## 8. Definition of Done (projektweit)

Ein Arbeitspaket gilt erst als fertig, wenn:
- [ ] Akzeptanzkriterien des jeweiligen Dokuments erfüllt
- [ ] Tests grün, inkl. der Safety-Tests, falls betroffen
- [ ] Keine PII in externen LLM-Prompts (falls LLM betroffen)
- [ ] `uv`-only, keine `pip`-Aufrufe
- [ ] Zugehöriges GitHub-Issue geschlossen, Epic-Checkliste aktualisiert
