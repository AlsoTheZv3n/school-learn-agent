its-platform/
├── apps/
│   ├── api/                          # FastAPI backend
│   │   ├── pyproject.toml             # uv-managed, no pip
│   │   ├── uv.lock
│   │   └── src/its/
│   │       ├── main.py                # app factory, router mounts
│   │       ├── config.py
│   │       │
│   │       ├── db/
│   │       │   ├── session.py         # sets per-request DB role → RLS keys off this
│   │       │   ├── models.py          # students, skills, attempts, notes, edges
│   │       │   └── migrations/        # alembic; RLS policies live in versioned SQL
│   │       │
│   │       ├── safety/                # ← the isolation gate. build first.
│   │       │   ├── rls.sql            # row-level security policies (student/teacher/admin)
│   │       │   ├── cohort.py          # min-cohort threshold: refuse aggregates where n < k
│   │       │   └── scoping.py         # resolves which role/student_id a request runs as
│   │       │
│   │       ├── retrieval/             # the three modes, all hitting one Postgres
│   │       │   ├── router.py          # decides scope: semantic / individual / population
│   │       │   ├── semantic.py        # pgvector similarity over study material (shared)
│   │       │   ├── individual.py      # scoped query, one student_id
│   │       │   ├── population.py      # GROUP BY aggregates → always via cohort.py
│   │       │   └── graph.py           # [[wikilink]] traversal via recursive CTE on edges
│   │       │
│   │       ├── agent/                 # LangGraph
│   │       │   ├── graph.py           # state machine wiring the nodes below
│   │       │   ├── state.py
│   │       │   └── nodes/
│   │       │       ├── route.py
│   │       │       ├── retrieve.py
│   │       │       ├── assess.py      # curated answer key, NOT free generation
│   │       │       ├── update_model.py# writes mastery back to learner_model
│   │       │       └── explain.py     # the low-stakes generative path
│   │       │
│   │       ├── learner_model/         # the open learner model
│   │       │   ├── bkt.py             # Bayesian Knowledge Tracing (NumPy), interpretable
│   │       │   ├── tracing.py         # update mastery from each attempt
│   │       │   └── dkt.py             # placeholder — swap in only once data justifies it
│   │       │
│   │       ├── grading/               # ← the one real plugin seam (Strategy/Adapter)
│   │       │   ├── base.py            # GraderStrategy protocol
│   │       │   ├── registry.py        # keyed on subject
│   │       │   ├── math.py            # symbolic/numeric check
│   │       │   ├── language.py
│   │       │   └── history.py         # open-response
│   │       │
│   │       ├── content/               # Obsidian-style KB ingestion
│   │       │   ├── parser.py          # splits prose from ```sql code fences
│   │       │   └── ingest.py          # embeds prose only; query kept as sidecar metadata
│   │       │
│   │       ├── llm/
│   │       │   ├── client.py          # frontier API or local Qwen
│   │       │   ├── anonymize.py       # strips PII before any prompt leaves the box
│   │       │   └── prompts/
│   │       │
│   │       ├── auth/
│   │       │   ├── roles.py           # student / teacher / admin — drives RLS
│   │       │   └── deps.py
│   │       │
│   │       └── api/
│   │           ├── student.py         # session screen endpoints
│   │           └── teacher.py         # dashboard + intervention endpoints
│   │
│   └── web/                          # React + TypeScript
│       ├── package.json
│       └── src/
│           ├── main.tsx
│           ├── api/client.ts
│           ├── components/
│           ├── student/              # the calm one-concept-at-a-time view
│           │   ├── SessionScreen.tsx
│           │   ├── MasteryBar.tsx    # gentle % — not the raw estimate
│           │   └── TutorThread.tsx
│           └── teacher/              # the dense oversight view
│               ├── Dashboard.tsx
│               ├── LearnerModelPanel.tsx  # shows the model + its uncertainty
│               └── InterventionControls.tsx
│
├── content/                          # the actual markdown vault (curated)
│   └── math/
│       ├── quadratic-equations.md    # prose + ```sql blocks for live detail
│       └── _links.md
│
├── infra/
│   ├── docker-compose.yml            # postgres + pgvector for local dev
│   ├── Caddyfile
│   └── deploy/                       # CH/EU region target (Azure CH / Exoscale)
│
├── tests/
│   ├── test_rls.py                   # prove a student CANNOT read another's rows
│   ├── test_cohort_threshold.py      # prove small cohorts are refused
│   └── test_grading/
│
├── .env.example
└── README.md