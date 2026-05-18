# db — Agent Guide

**Owner**: member 3 (Storage Engineer)

## Mission

Provide SQLite persistence for feeds, entries, tags, agent results (summaries, translations), and usage statistics. Manage schema migrations. This is a **library**, not an HTTP module — other modules import functions from here, the frontend never talks to this directly.

## Contract (Python)

Suggested module layout:

```
db/
  __init__.py        public API re-exports
  connection.py      get_connection() / async session factory
  migrations/        versioned schema files
  repositories/
    feed_repo.py     CRUD for Feed
    entry_repo.py    CRUD + queries for Entry (filter by feed/tag/read state)
    tag_repo.py      CRUD for Tag
    agent_repo.py    cache for SummaryResult / TranslationResult
    usage_repo.py    UsageBucket aggregation
```

Repository functions take and return `app.schemas` Pydantic models. Internal row tuples never leak.

## Dependencies

- May add `sqlite-utils`, `aiosqlite`, or stick with stdlib `sqlite3` — your call.
- Must NOT import `feed_engine`, `content_cleaner`, `agent_*`, or `llm_providers` (you are at the bottom of the dependency graph).
- Schema is initialized via the FastAPI lifespan in `app/lifespan.py`. Add an `init_db()` call there when ready.

## Non-Goals

- HTTP endpoints (this is a library).
- Data fetching from the network.
- Business rules — repositories are dumb CRUD; logic lives in the calling modules.

## Acceptance Criteria

1. Schema versioned and migrations replayable on a fresh DB.
2. All public functions accept/return Pydantic models from `app.schemas`.
3. Concurrent reads do not block writes (use WAL mode).
4. Foreign keys enforced (`PRAGMA foreign_keys=ON`).
5. Unit tests use an in-memory SQLite (`:memory:`) so they run fast and isolated.
6. `uv run pytest` and `uv run ruff check` pass.

## References

- `app/schemas/` — all model shapes
- `app/config.py` — `settings.resolved_db_path()` is where the file lives
- `backend/AGENT.md`
