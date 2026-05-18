# feed_engine — Agent Guide

**Owner**: member 2 (Feed Engineer)

## Mission

Provide RSS/Atom/OPML parsing, feed sync, and import/export over HTTP. This is the only place that talks to the public internet to fetch feed XML.

## Contract (HTTP)

Mounted at `/feeds`. Suggested endpoints (extend as needed; document additions in `docs/ipc-contract.md`):

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/feeds` | list all subscribed feeds (returns `Feed[]`) |
| `POST` | `/feeds` | subscribe by URL (auto-discovery allowed) |
| `DELETE` | `/feeds/{id}` | unsubscribe |
| `POST` | `/feeds/{id}/sync` | fetch and persist new entries; returns `LongTaskStatus` |
| `POST` | `/feeds/sync-all` | sync every feed |
| `POST` | `/opml/import` | import OPML file (multipart) |
| `GET` | `/opml/export` | download OPML file |

Use `app.schemas.Feed` and `app.schemas.Entry`. Do not redefine these.

## Dependencies

- May import from `db` (entry/feed persistence).
- May add libraries via `pyproject.toml` (suggest `feedparser`, `httpx`, `defusedxml`).
- Must NOT import `content_cleaner` directly — entries are stored raw; cleaning happens on read.
- Must NOT import any `agent_*` module.

## Non-Goals

- HTML cleaning / Markdown conversion (that's `content_cleaner`).
- Summary or translation (those are `agent_*`).
- Any UI concerns.

## Acceptance Criteria

1. `GET /feeds` returns valid `Feed` objects matching the Pydantic schema.
2. `POST /feeds/{id}/sync` is idempotent — re-syncing does not create duplicate entries.
3. OPML import handles nested `<outline>` groups.
4. Network errors surface as `502` or `504` with a structured error body, not 500.
5. Unit tests cover the parser with at least one RSS 2.0, one Atom, and one OPML fixture.
6. `uv run pytest` and `uv run ruff check` pass.

## References

- `app/schemas/feed.py` and `app/schemas/entry.py` — authoritative shapes
- `backend/AGENT.md` — workspace-level rules
- Mercury reference UI: `packages/ui/src/domain/fixtures.ts` shows the kind of data the UI expects
