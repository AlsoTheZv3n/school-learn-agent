# Detailplanung (Planning)

Diese Ebene **vertieft** das Fundament aus [docs/](../) (00-11). Sie entstand durch je einen Planungs-Agenten pro Epic und besteht aus drei Teilen:

1. **Pro-Epic-Detailplanung** (diese Mappe) - Scope, Task-Reihenfolge, feinere Sub-Tasks, Designentscheidungen, Risiken, offene Fragen, Test-Strategie.
2. **Pro-Task-Issue-Bodies** in [../issues/](../issues/) - je eine eigenstaendige, umsetzbare .md pro Task (FND-1.md ...), die als GitHub-Issue-Body dient.
3. **Konsolidierte offene Fragen & Risiken** - [open-questions-and-risks.md](open-questions-and-risks.md).

Die GitHub-Struktur (Labels, Milestones M0-M6, 14 Epics, 50 Sub-Issues) wird aus [../../scripts/issues.manifest.json](../../scripts/issues.manifest.json) via [ootstrap_github.ps1](../../scripts/bootstrap_github.ps1) / [.sh](../../scripts/bootstrap_github.sh) erzeugt.

## Epic-Detailplanung

| Epic | Milestone | Detailplanung | Quelle |
|------|-----------|---------------|--------|
| **E1** Foundations: Monorepo, Infra, Skeleton | M0 Foundations | [E1-foundations.md](E1-foundations.md) | [02-foundations.md](../02-foundations.md) |
| **E2** Database: Schema & Migrationen | M1 Data Layer & Safety | [E2-database.md](E2-database.md) | [03-database.md](../03-database.md) |
| **E3** Safety & Isolation (RLS + Min-Cohort) | M1 Data Layer & Safety | [E3-safety-isolation.md](E3-safety-isolation.md) | [04-safety.md](../04-safety.md) |
| **E4** Retrieval: Router + 3 Modi + Graph | M2 Retrieval & Content | [E4-retrieval.md](E4-retrieval.md) | [05-retrieval.md](../05-retrieval.md) |
| **E5** Content-Ingestion (Markdown-Vault) | M2 Retrieval & Content | [E5-content-ingestion.md](E5-content-ingestion.md) | [05-retrieval.md](../05-retrieval.md) |
| **E6** Learner-Modell (BKT) | M3 Learning Engine | [E6-learner-model.md](E6-learner-model.md) | [06-learner-model-and-grading.md](../06-learner-model-and-grading.md) |
| **E7** Grading-Strategy-Registry | M3 Learning Engine | [E7-grading.md](E7-grading.md) | [06-learner-model-and-grading.md](../06-learner-model-and-grading.md) |
| **E8** Agent-Loop (LangGraph) | M3 Learning Engine | [E8-agent-loop.md](E8-agent-loop.md) | [07-agent.md](../07-agent.md) |
| **E9** Backend-API (Student + Teacher) | M4 API & Frontend | [E9-backend-api.md](E9-backend-api.md) | [08-backend-api.md](../08-backend-api.md) |
| **E10** Frontend: Schueler-Session | M4 API & Frontend | [E10-frontend-student.md](E10-frontend-student.md) | [09-frontend.md](../09-frontend.md) |
| **E11** Frontend: Lehrer-Dashboard | M4 API & Frontend | [E11-frontend-teacher.md](E11-frontend-teacher.md) | [09-frontend.md](../09-frontend.md) |
| **E12** Testing & CI | M6 Hardening | [E12-testing-ci.md](E12-testing-ci.md) | [10-testing.md](../10-testing.md) |
| **E13** Mock-Data-Seeder | M5 Data & Production | [E13-mock-data.md](E13-mock-data.md) | [11-mock-data-and-production.md](../11-mock-data-and-production.md) |
| **E14** Produktionsdaten & Compliance | M5 Data & Production | [E14-production-compliance.md](E14-production-compliance.md) | [11-mock-data-and-production.md](../11-mock-data-and-production.md) |

## Task-Issue-Bodies (../issues/)

- **E1**: [FND-1](../issues/FND-1.md) · [FND-2](../issues/FND-2.md) · [FND-3](../issues/FND-3.md) · [FND-4](../issues/FND-4.md) · [FND-5](../issues/FND-5.md) · [FND-6](../issues/FND-6.md)
- **E2**: [DB-1](../issues/DB-1.md) · [DB-2](../issues/DB-2.md) · [DB-3](../issues/DB-3.md) · [DB-4](../issues/DB-4.md)
- **E3**: [SAF-1](../issues/SAF-1.md) · [SAF-2](../issues/SAF-2.md) · [SAF-3](../issues/SAF-3.md) · [SAF-4](../issues/SAF-4.md)
- **E4**: [RET-1](../issues/RET-1.md) · [RET-2](../issues/RET-2.md) · [RET-3](../issues/RET-3.md) · [RET-4](../issues/RET-4.md) · [RET-5](../issues/RET-5.md)
- **E5**: [CON-1](../issues/CON-1.md) · [CON-2](../issues/CON-2.md) · [CON-3](../issues/CON-3.md)
- **E6**: [LM-1](../issues/LM-1.md) · [LM-2](../issues/LM-2.md) · [LM-3](../issues/LM-3.md)
- **E7**: [GR-1](../issues/GR-1.md) · [GR-2](../issues/GR-2.md) · [GR-3](../issues/GR-3.md)
- **E8**: [AG-1](../issues/AG-1.md) · [AG-2](../issues/AG-2.md) · [AG-3](../issues/AG-3.md)
- **E9**: [API-1](../issues/API-1.md) · [API-2](../issues/API-2.md) · [API-3](../issues/API-3.md)
- **E10**: [FE-S1](../issues/FE-S1.md) · [FE-S2](../issues/FE-S2.md) · [FE-S3](../issues/FE-S3.md)
- **E11**: [FE-T1](../issues/FE-T1.md) · [FE-T2](../issues/FE-T2.md) · [FE-T3](../issues/FE-T3.md)
- **E12**: [TST-1](../issues/TST-1.md) · [TST-2](../issues/TST-2.md) · [TST-3](../issues/TST-3.md) · [TST-4](../issues/TST-4.md)
- **E13**: [MOCK-1](../issues/MOCK-1.md) · [MOCK-2](../issues/MOCK-2.md) · [MOCK-3](../issues/MOCK-3.md)
- **E14**: [PROD-1](../issues/PROD-1.md) · [PROD-2](../issues/PROD-2.md) · [PROD-3](../issues/PROD-3.md)

## Querschnitt

- [open-questions-and-risks.md](open-questions-and-risks.md) - konsolidierte offene Entscheidungen und Risiken aus allen Epics.
- [../00-architecture.md](../00-architecture.md) - nicht verhandelbare Prinzipien P1-P9 (gelten ueber allem).

