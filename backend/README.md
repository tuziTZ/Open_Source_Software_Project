# Lumen Backend

Python FastAPI sidecar for the Lumen desktop app. Runs as a child process of the Tauri shell.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) for dependency management

## Setup

```bash
uv sync
```

## Run (development)

```bash
uv run uvicorn app.main:app --reload
```

Server binds to `127.0.0.1:8000` by default. Configurable via `MERCURY_*` env vars (see `app/config.py`).

Endpoints:
- `GET /healthz` — liveness probe
- `GET /docs` — OpenAPI schema browser
- `GET /openapi.json` — schema used to regenerate `packages/shared-types`

## Test

```bash
uv run pytest
uv run ruff check
```

## Module Map

| Folder | Owner | Role |
|---|---|---|
| `app/` | tech lead | composition root, schemas, lifespan |
| `feed_engine/` | member 2 | RSS/Atom/OPML — HTTP |
| `db/` | member 3 | SQLite, repositories — library |
| `content_cleaner/` | member 4 | HTML cleaning, readability, markdown — HTTP |
| `agent_summary/` | member 6 | summary agent — HTTP |
| `agent_translation/` | member 7 | translation agent — HTTP |
| `llm_providers/` | member 8 | LLM clients (OpenAI-compatible, Ollama) — library |

Each module folder has its own `AGENT.md` describing scope, contract, and acceptance criteria.
