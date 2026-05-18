# Mercury Architecture

## Overview

Mercury is a local-first, cross-platform RSS reader. The desktop application is a single Tauri window hosting a React frontend that communicates with a Python (FastAPI) backend over HTTP on localhost. No data leaves the user's machine unless an LLM provider is configured.

## Process Model

```
+----------------------------------------------------+
|  Tauri Shell (Rust, ~5-15 MB)                      |
|  - owns the OS window, tray, file dialogs          |
|  - spawns the Python sidecar on startup            |
|  - kills the sidecar on close                      |
|                                                    |
|  +---------------------------+   +---------------+ |
|  | WebView (React UI)        |   | Python sidec. | |
|  | packages/ui               |<--|  FastAPI app  | |
|  |  - fetch() to 127.0.0.1   |   |  backend/     | |
|  +---------------------------+   +---------------+ |
+----------------------------------------------------+
                                          |
                                          v
                                   +---------------+
                                   | SQLite file   |
                                   | ~/.mercury/   |
                                   +---------------+
                                          |
                                          v
                                   +---------------+
                                   | LLM provider  |
                                   | (optional,    |
                                   |  user config) |
                                   +---------------+
```

- One Tauri process, one Python process. No multi-process backend.
- Python sidecar binds to `127.0.0.1` on a port from `MERCURY_PORT` (default 8000). For production builds, the Tauri shell picks a free port and passes it to the webview as `window.__BACKEND_PORT__`.
- SQLite file lives under `~/.mercury/mercury.db` (configurable).
- The only outbound network traffic is feed fetching (`feed_engine`) and LLM calls (`llm_providers`).

## Layered Module Map

```
                  +-----------------------+
   Frontend       |   packages/ui (React) |
                  +----------+------------+
                             |
                             v
                  +-----------------------+
   Contract      | packages/shared-types  |  <-- generated from /openapi.json
                  |  packages/ipc-client  |
                  +----------+------------+
                             |  HTTP (localhost)
                             v
                  +-----------------------+
   HTTP layer    |   backend/app/main    |
                  |   (FastAPI + CORS)    |
                  +-+--------+--------+---+
                    |        |        |
        +-----------+   +----+----+   +---------------+
        v               v         v                   v
   feed_engine   content_cleaner  agent_summary   agent_translation
        \              |              |                /
         \             v              v               /
          \         +-----+      +-------+           /
           \------> | db  |      | llm_providers | <
                    +-----+      +-------+
```

Rules:
- HTTP modules (`feed_engine`, `content_cleaner`, `agent_summary`, `agent_translation`) may import library modules (`db`, `llm_providers`).
- HTTP modules MUST NOT call each other over HTTP — direct Python imports only.
- Library modules MUST NOT import HTTP modules.
- All cross-module data uses Pydantic models from `backend/app/schemas/`.

## Data Flow Examples

### Subscribing and reading a feed

1. User pastes URL → `POST /feeds` (`feed_engine`)
2. `feed_engine` validates, persists via `db`, kicks off a sync
3. Sync fetches RSS, parses, stores raw entries via `db`
4. UI requests `GET /feeds` → returns updated list with unread counts
5. User opens an entry → UI calls `POST /content/clean` (`content_cleaner`)
6. `content_cleaner` reads raw HTML from `db`, returns cleaned HTML + Markdown

### Summarizing an entry

1. UI calls `POST /agents/summary` with `entry_id` (`agent_summary`)
2. `agent_summary` checks cache via `db`
3. On miss, fetches `Entry.reader_html` from `db`, chunks, prompts via `llm_providers`
4. Result persisted to `db`, returned to UI

## Contract Sync

The frontend type contract is regenerated from the backend's OpenAPI schema:

```
backend/app/schemas/*.py  (Pydantic, single source of truth)
        |
        v
  FastAPI /openapi.json
        |
        v
  openapi-typescript
        |
        v
  packages/shared-types/src/generated.ts
        |
        v
  packages/ui imports types
```

Whenever a Pydantic model changes, run `pnpm gen:types` and commit the regenerated TS file in the same PR. The CI also regenerates and fails if `generated.ts` is stale.

## Non-Goals for the Architecture

- No multi-user / no auth — local-first
- No real-time bus between modules (no Redis, no event broker)
- No microservice split — one Python process is enough
- No remote feed sync — every install is independent
