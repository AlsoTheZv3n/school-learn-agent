# Sicherheits- & Prinzipien-Audit (M6 Hardening)

Querschnittliche Prüfung der nicht verhandelbaren Prinzipien (P1–P9, `docs/00`) gegen
die umgesetzte Implementierung (Stand: M0–M5 abgeschlossen). Jede Zeile nennt, **wo** das
Prinzip verankert ist und **wie** es getestet wird.

## Prinzipien-Konformität

| Prinzip | Verankerung | Test / Nachweis |
|---|---|---|
| **P1** Safety in der DB (RLS) | `safety/rls.sql`, Migration 0002 (RLS auf `attempts`, `learner_state`, `teacher_notes`, `enrollments`) | `test_rls.py` (Isolation), `test_hardening.py` (RLS aktiv + Policies vorhanden) — **CI-blockierend** |
| **P2** Kuratierte Bewertung | `grading/` (Answer-Key kuratiert in `content/items.py`), `assess`-Node nutzt Grader, nie LLM | `test_grading.py`, `test_agent_turn.py` (confidence 1.0) |
| **P3** Modell verbessert sich, nicht der Agent | `learner_model/tracing.py` (`record_attempt`); Agent-Verhalten = Funktion des Modells | `test_agent_turn.py` (Mastery steigt), `test_bkt.py` |
| **P4** PII verlässt die Maschine nicht | `llm/anonymize.py` (`scrub`) vor jedem externen Call; nur IDs/Skill-Keys an LLM | `test_anonymize.py` |
| **P5** Open Learner Model | Lehrer-Sicht zeigt `uncertainty`; Schüler-Sicht **nicht** (an der API erzwungen) | `test_api.py`, `test_e2e_smoke.py` |
| **P6** Mensch im Loop | Lehrer-Override (`teacher_notes.override_mastery`); niedrige Grader-Konfidenz wird nicht zementiert (`update_model` ≥ 0.9) | `test_api.py` (Notiz), `grading/history.py` |
| **P7** Genau eine Plugin-Naht | nur `grading/` ist Registry; `retrieval/`, `agent/`, `learner_model/` flach | Code-Struktur (Registry nur in `grading/registry.py`) |
| **P8** Datenresidenz CH/EU | `docs/compliance.md`, `DATA_MODE`-Guards, getrennte DB-URLs | `test_seed.py` (Guards) |
| **P9** `uv` ausschliesslich | `pyproject.toml` + `uv.lock`; CI nutzt nur `uv` | `ci.yml` (kein `pip`) |
| **Aggregat-Leak** (Min-Cohort) | `safety/cohort.py`; jede Population-Query via `enforce_min_cohort` | `test_cohort_threshold.py`, `test_api.py` (403) |

## CI-Härtung

- **Vorgelagerter Safety-Gate** (blockierend): `test_rls.py` + `test_cohort_threshold.py`
  laufen vor der vollen Suite gegen echtes Postgres mit RLS (`ci.yml`).
- Zwei Jobs: `test` (pytest gegen Postgres-Service) und `web` (tsc + vite build).

## Bewusste Stubs — Gates VOR Produktivbetrieb

Diese sind absichtlich vereinfacht und **müssen** vor echtem Betrieb ersetzt werden:

1. **Auth (FND-5)**: `current_principal` ist ein Stub (`NotImplementedError`). Tests
   injizieren das Principal. → Echtes JWT/IdP (Keycloak/Entra), Claims→Rolle/`student_id`,
   Signaturprüfung gegen `JWT_PUBLIC_KEY`.
2. **LLM-Client (AG-3)**: lokaler Backend ist ein deterministischer Stub; Frontier nicht
   verdrahtet. → Lokales Modell (Qwen2.5) oder Frontier-API **mit AVV + No-Training**.
   Der `scrub`-Pfad (P4) und der Backend-Schalter stehen bereits.
3. **Embedder (RET-2/CON-2)**: `HashingEmbedder` ist ein deterministischer Stub. → Echtes
   Embedding-Modell; finale `EMBEDDING_DIM` fixieren (ggf. Schema-Migration + Re-Embed).
4. **Frontend-E2E (TST-4)**: HTTP-Smoke vorhanden; Browser-E2E (Playwright) offen.

Vollständige Liste offener Entscheidungen: `docs/planning/open-questions-and-risks.md`.
Compliance-Checkliste vor Go-Live: `docs/compliance.md` §6.
