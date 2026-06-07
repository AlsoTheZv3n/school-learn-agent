# its-api

FastAPI backend for the ITS Platform. Managed exclusively with [`uv`](https://docs.astral.sh/uv/) (no `pip`, principle P9).

```bash
# from repo root: start the database first
docker compose -f infra/docker-compose.yml up -d

# in this directory
uv sync                                   # create .venv + uv.lock
uv run uvicorn its.main:app --reload      # http://localhost:8000/health
uv run pytest                             # run the test suite
```

Source layout: `src/its/` (see `docs/00-architecture.md` §6 for the target module map).
