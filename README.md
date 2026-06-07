# ITS Platform — Implementierungsplan

Ein Intelligent Tutoring System (ITS): Lernmaterial pro Stufe/Fach, ein individueller
Lernstand pro Schüler:in, ein Agent der erklärt und abfragt, sowie eine Lehrer:innen-Ansicht
zur Kontrolle und Intervention — auf einer datenschutzkonformen Datenbasis.

Dieses Verzeichnis enthält die **vollständige Planung**, aufgeteilt in einzeln umsetzbare
Arbeitspakete. Es ist so aufbereitet, dass **Claude Code** das Projekt Schritt für Schritt
umsetzen kann — beginnend mit dem Anlegen von GitHub-Milestones, -Epics und -Issues.

---

## Für Claude Code — Reihenfolge der Umsetzung

> **Schritt 0 (zuerst):** Lies [`docs/00-architecture.md`](docs/00-architecture.md) vollständig.
> Dort stehen die **nicht verhandelbaren Prinzipien** (Safety zuerst, kuratierte Antworten,
> PII-Anonymisierung, BKT vor DKT, genau eine Plugin-Naht). Halte dich in jedem Arbeitspaket
> daran.
>
> **Schritt 1:** Setze die GitHub-Struktur gemäss [`docs/01-github-issues.md`](docs/01-github-issues.md)
> um (Labels → Milestones → Epics → Issues). Erst danach mit Code beginnen.
>
> **Schritt 2 ff.:** Arbeite die Dokumente `02` bis `11` in numerischer Reihenfolge ab. Jedes
> Dokument nennt seine Voraussetzungen, die zu erstellenden Dateien, konkrete Schemata/Signaturen,
> Akzeptanzkriterien und die zugehörigen Issue-Keys.

Jedes Implementierungsdokument endet mit einem Abschnitt **„Claude-Code-Prompt"** — ein
copy-paste-fähiger Auftrag, der dieses eine Arbeitspaket abgeschlossen umsetzt.

---

## Dokumentenindex

| # | Datei | Inhalt | GitHub-Epic |
|---|-------|--------|-------------|
| 00 | [`docs/00-architecture.md`](docs/00-architecture.md) | Architektur, Tech-Stack, Kernprinzipien, Constraints | — |
| 01 | [`docs/01-github-issues.md`](docs/01-github-issues.md) | Milestones, Epics, Issues + `gh`-Bootstrap | — |
| 02 | [`docs/02-foundations.md`](docs/02-foundations.md) | Monorepo, Docker (Postgres+pgvector), FastAPI-Skeleton, `uv` | `E1` |
| 03 | [`docs/03-database.md`](docs/03-database.md) | Schema, SQLAlchemy-Modelle, Alembic-Migrationen | `E2` |
| 04 | [`docs/04-safety.md`](docs/04-safety.md) | RLS-Policies, Min-Cohort-Schwelle, Scoping | `E3` |
| 05 | [`docs/05-retrieval.md`](docs/05-retrieval.md) | Router + 3 Modi (semantic/individual/population) + Graph + Ingestion | `E4`, `E5` |
| 06 | [`docs/06-learner-model-and-grading.md`](docs/06-learner-model-and-grading.md) | BKT-Lernmodell + `GraderStrategy`-Registry | `E6`, `E7` |
| 07 | [`docs/07-agent.md`](docs/07-agent.md) | LangGraph-Loop, LLM-Client, Anonymisierung, Prompts | `E8` |
| 08 | [`docs/08-backend-api.md`](docs/08-backend-api.md) | Student- & Lehrer-Endpoints, Schemas, Auth-Deps | `E9` |
| 09 | [`docs/09-frontend.md`](docs/09-frontend.md) | React/TS: Schüler-Session + Lehrer-Dashboard | `E10`, `E11` |
| 10 | [`docs/10-testing.md`](docs/10-testing.md) | Teststrategie, Safety-Tests, Fixtures, CI | `E12` |
| 11 | [`docs/11-mock-data-and-production.md`](docs/11-mock-data-and-production.md) | Mock-Seeder + Produktionsdaten-Pfad + Env-Toggles | `E13`, `E14` |

---

## Kurzüberblick Tech-Stack

| Architekturteil | Wahl |
|---|---|
| Vektorstore + relationale Daten + Kohorten-Aggregate | **ein** PostgreSQL + `pgvector` |
| Link-Graph (Obsidian-Stil) | `edges`-Tabelle + rekursive CTE |
| Safety- & Isolations-Gate | Postgres **Row-Level Security** + Min-Cohort-Check |
| Retrieval-Router + Agent-Loop | **LangGraph** |
| Lernmodell | **Bayesian Knowledge Tracing** (NumPy) → DKT später |
| Erklärung/Umformulierung | Frontier-API (anonymisiert) **oder** lokal (Qwen2.5) |
| Backend / Frontend | **FastAPI** + **React/TypeScript** |
| Auth + Hosting | Keycloak/Entra ID + CH/EU-Region |
| Fachspezifische Bewertung | `GraderStrategy`-Adapter (einzige Plugin-Naht) |
| Python-Tooling | **`uv`** ausschliesslich (kein `pip`) |

---

## Compliance-Hinweis

Diese Plattform verarbeitet identifizierbare Daten über **Minderjährige**. Datenresidenz
(CH/EU, revDSG/DSGVO), PII-Minimierung im LLM-Pfad und die Isolationsgarantien sind
**keine optionalen Features**, sondern Voraussetzung. Die rechtlichen Detailangaben in
[`docs/11`](docs/11-mock-data-and-production.md) sind gegen **aktuelle** Quellen zu prüfen,
da sich Vorgaben für Ed-Tech laufend ändern können.
