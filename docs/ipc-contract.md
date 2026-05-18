# IPC Contract

The frontend and backend communicate over HTTP on localhost. This document is the canonical list of endpoints, kept in sync with `backend/app/main.py` and the per-module routers.

## Base URL

- Dev: `http://127.0.0.1:8000`
- Packaged: `http://127.0.0.1:${window.__BACKEND_PORT__}` (set by the Tauri shell at boot)

## Type Sync

All request/response shapes are Pydantic models in `backend/app/schemas/`. The TS frontend imports them from `@mercury/shared-types`, which is regenerated from `/openapi.json`.

After changing any model or route signature:

```bash
pnpm gen:types
```

Commit the updated `packages/shared-types/src/generated.ts` in the same PR.

## Endpoint Table

Owners populate this table as endpoints land. Format: `METHOD path → response`.

### Meta (tech lead)

| Method | Path | Body | Response | Notes |
|---|---|---|---|---|
| GET | `/healthz` | — | `{ status: "ok" }` | liveness probe |

### Feeds (member 2)

| Method | Path | Body | Response | Notes |
|---|---|---|---|---|
| (planned) | `/feeds/*` | | | see `backend/feed_engine/AGENT.md` |

### Content (member 4)

| Method | Path | Body | Response | Notes |
|---|---|---|---|---|
| (planned) | `/content/*` | | | see `backend/content_cleaner/AGENT.md` |

### Summary Agent (member 6)

| Method | Path | Body | Response | Notes |
|---|---|---|---|---|
| (planned) | `/agents/summary/*` | | | see `backend/agent_summary/AGENT.md` |

### Translation Agent (member 7)

| Method | Path | Body | Response | Notes |
|---|---|---|---|---|
| (planned) | `/agents/translation/*` | | | see `backend/agent_translation/AGENT.md` |

## Breaking-Change Policy

A breaking change is:
- Removing or renaming a route, query param, or response field
- Changing a response field's type
- Making a previously-optional field required

Before merging a breaking change:
1. Coordinate with the UI engineer (member 5) and any downstream module owners
2. Update both the backend and the UI in the same PR (or in two sequenced PRs the same day)
3. Note the change in the PR description

Additions (new endpoint, new optional field) are non-breaking and do not require coordination beyond review.

## Error Format

All errors return JSON:

```json
{
  "detail": "human-readable message",
  "code": "MACHINE_READABLE_CODE",
  "context": {}
}
```

- `4xx` for user errors (bad input, not found)
- `5xx` for internal errors (DB unavailable, upstream provider down)
- Never raise an unhandled exception; FastAPI converts those to opaque 500s

Use `HTTPException` from FastAPI with a structured `detail`.
