## Ziel

Ein lokaler **Postgres 16 + pgvector**-Container ist via Docker-Compose startbar, fährt mit aktivierten Extensions `vector` und `uuid-ossp` hoch und meldet sich über einen Healthcheck als `healthy`. Eine `.env.example` dokumentiert die nötigen Umgebungsvariablen.

## Kontext & Prinzipien

- **P1 (Safety in der DB) / Tech-Stack:** Es gibt **genau eine** Datenbank für alle drei Retrieval-Modi (Semantic via `pgvector`, Individual via RLS-Queries, Population via Aggregate) — keine separate Vektor-DB. Dieser Task legt diese eine DB an.
- **P8 (CH/EU-Datenresidenz):** Docker-Compose ist ausdrücklich nur für den lokalen Prototyp. `.env.example` enthält `LLM_BACKEND=local` als sicheren Default, damit kein PII an externe APIs geht, bevor die Anonymisierung (P4) existiert. Produktions-Hosting in CH/EU ist ein späterer Infra-Task.
- **P4 (PII):** `.env.example` enthält Platzhalter (`LLM_API_KEY=` leer), niemals echte Keys; die echte `.env` ist via `.gitignore` ausgeschlossen (FND-1).

## Zu erstellende/ändernde Dateien

```
infra/docker-compose.yml
infra/init/01-extensions.sql      # wird beim ersten Container-Start ausgeführt
.env.example                      # im Repo-Root (nicht in infra/)
```

## Schnittstellen & Signaturen

`infra/docker-compose.yml` (aus `docs/02` Section 3):

```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: its
      POSTGRES_PASSWORD: its_dev_pw
      POSTGRES_DB: its
    ports:
      - "5432:5432"
    volumes:
      - its_pgdata:/var/lib/postgresql/data
      - ./init:/docker-entrypoint-initdb.d:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U its -d its"]
      interval: 5s
      timeout: 5s
      retries: 10
volumes:
  its_pgdata:
```

`infra/init/01-extensions.sql` (aus `docs/02` Section 3):

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

`.env.example` (Repo-Root, aus `docs/02` Section 3):

```dotenv
DATABASE_URL=postgresql+psycopg://its:its_dev_pw@localhost:5432/its
DATA_MODE=mock          # mock | prod  (siehe docs/11)
MIN_COHORT_K=10
LLM_BACKEND=local       # local | frontier
LLM_API_KEY=
JWT_PUBLIC_KEY=
```

## Umsetzungsschritte

- [ ] `infra/docker-compose.yml` mit obigem Inhalt anlegen.
- [ ] `infra/init/01-extensions.sql` mit den beiden `CREATE EXTENSION`-Statements anlegen.
- [ ] `.env.example` im Repo-Root anlegen (Werte exakt wie oben, `LLM_API_KEY`/`JWT_PUBLIC_KEY` leer lassen).
- [ ] Container starten: `docker compose -f infra/docker-compose.yml up -d`.
- [ ] Auf `healthy` warten, dann verifizieren, dass die Extensions geladen sind.
- [ ] Beachten: Die `init/`-Skripte laufen **nur** beim ersten Start mit leerem Volume — bei Änderungen Volume zurücksetzen (`docker compose ... down -v`).

## Akzeptanzkriterien

- [ ] `docker compose -f infra/docker-compose.yml up -d` startet den `db`-Service ohne Fehler.
- [ ] `docker compose ... ps` zeigt den Service als `healthy`.
- [ ] In der DB sind die Extensions `vector` und `uuid-ossp` aktiv.
- [ ] `.env.example` existiert im Repo-Root mit allen sechs Variablen; keine echten Secrets enthalten.
- [ ] `DATABASE_URL` nutzt den `postgresql+psycopg://`-Treiber (passend zu `psycopg[binary]` aus FND-2).

## Tests / Verifikation

```bash
docker compose -f infra/docker-compose.yml up -d
docker compose -f infra/docker-compose.yml ps          # erwartet: db ... (healthy)
docker compose -f infra/docker-compose.yml exec db \
  psql -U its -d its -c "SELECT extname FROM pg_extension ORDER BY extname;"
# erwartet: enthält 'uuid-ossp' und 'vector'
docker compose -f infra/docker-compose.yml exec db pg_isready -U its -d its  # erwartet: accepting connections
```

## Abhängigkeiten

- **Abhängig von:** FND-1 — `infra/` und der Repo-Root müssen existieren.
- **Nachgelagert:** FND-6 (CI nutzt dasselbe `pgvector/pgvector:pg16`-Image als Service), E2/DB (`docs/03`, Alembic-Migrationen gegen diese DB), E3/Safety (RLS-Policies gegen diese DB).

## Definition of Done

- [ ] Akzeptanzkriterien dieses Tasks erfüllt.
- [ ] Verifikation oben ausgeführt: Service `healthy`, beide Extensions aktiv.
- [ ] Keine PII/Secrets committet (`.env.example` nur mit Platzhaltern; `.env` ignoriert).
- [ ] CH/EU-Hinweis dokumentiert (Compose nur Prototyp, `LLM_BACKEND=local` Default).
- [ ] `uv`-only-Konvention unberührt (kein `pip` in diesem Task).
- [ ] GitHub-Issue FND-3 geschlossen, E1-Epic-Checkliste aktualisiert.
