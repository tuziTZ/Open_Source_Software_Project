# Backend Agent Guide

Workspace-level rules for everyone writing code under `backend/`.

## Stack

- Python 3.11+
- FastAPI (single process)
- Pydantic v2 for all serialized models
- `uv` for dependency management
- `pytest` for tests, `ruff` for lint
- SQLite for persistence (owned by `db/`)

## Layout

```
backend/
  app/              composition root (tech lead)
    main.py         FastAPI app + router mounting
    config.py       env-driven settings
    lifespan.py     startup/shutdown
    schemas/        Pydantic models shared across modules
  feed_engine/      HTTP-facing module
  db/               library — imported by other modules, never exposes HTTP
  content_cleaner/  HTTP-facing module
  agent_summary/    HTTP-facing module
  agent_translation/ HTTP-facing module
  llm_providers/    library — imported by agent_* modules
  tests/            integration tests (TestClient); unit tests live next to code
```

## Rules

1. **Schemas live in `app/schemas/`**. Module-specific request/response types may live in the module, but anything shared with the frontend (Feed, Entry, Tag, etc.) must come from `app/schemas/`.
2. **Routers are mounted in `app/main.py`**. When you add a new router, update `main.py` and `docs/ipc-contract.md`.
3. **Library modules (`db`, `llm_providers`) do not import FastAPI**. They expose Python functions/classes only.
4. **HTTP modules do not call each other over HTTP**. Import the function directly.
5. **Errors**: raise `HTTPException` for user-visible errors. Use codes from `app/schemas/common.py` where applicable.
6. **No global mutable state** except `app/config.py:settings`. Use FastAPI dependencies for per-request resources.
7. **Tests**: each module owns its tests. Use the `client` fixture from `tests/conftest.py` for HTTP tests.
8. **Logging**: use `logging.getLogger(__name__)`, not `print`.

## Adding a Dependency

Add to `pyproject.toml` under `[project].dependencies` (runtime) or `[dependency-groups].dev` (dev only), then:

```bash
uv lock
uv sync
```

Commit both `pyproject.toml` and `uv.lock`.

## After Changing a Pydantic Model

The frontend types are regenerated from `/openapi.json`. After changing any model in `app/schemas/` or any router signature, regenerate:

```bash
pnpm gen:types
```

Commit the updated `packages/shared-types/src/generated.ts` in the same PR.
