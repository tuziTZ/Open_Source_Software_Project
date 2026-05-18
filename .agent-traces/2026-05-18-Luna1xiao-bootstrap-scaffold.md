# Bootstrap Scaffold

- Member: @Luna1xiao
- Date: 2026-05-18
- Agent: Claude Code (Opus 4.7)
- Related PR: (pending — first integration PR on branch `Luna1xiao/bootstrap`)

## Goal

Lay down the repository skeleton so the other eight members can start working in parallel: backend composition root, Pydantic schemas, per-module stubs with AGENT.md contracts, type-generation pipeline, governance files, and architecture docs.

## Approach

Tauri shell hosting `packages/ui`, with a Python FastAPI sidecar as the single backend process. Pydantic models in `backend/app/schemas/` are the single source of truth; `/openapi.json` is piped through `openapi-typescript` into `packages/shared-types/src/generated.ts`, which `packages/ui` and `packages/ipc-client` consume. Each module gets only an empty router (HTTP modules) or `__init__.py` (library modules) plus an `AGENT.md` — owners write the first real code.

## Decisions

- **Python backend over Node** — team is more comfortable with Python; many target libraries (`feedparser`, `readability-lxml`, LLM SDKs) are Python-native.
- **Single FastAPI process** instead of per-module processes — simpler launch, one IPC channel, easier debugging.
- **`uv` over Poetry/pip** — fastest install, locked deps, modern.
- **`db` and `llm_providers` are libraries, not HTTP modules** — they're internal infrastructure imported by others; exposing them over HTTP would blur module boundaries.
- **Tech lead writes contracts and skeletons only** — initial plan had `service.py`/`parser.py`/`prompts.py` per module; user corrected that those belong to owners' first commits. Re-scoped to: schemas, app entry, empty routers, AGENT.md files, docs, CI.

## Surprises

- `packages/ui/src/domain/types.ts` already had rich `Feed`/`Entry`/`Tag` interfaces — Pydantic models could be derived 1:1 instead of designed fresh.
- `ruff` flagged tab indentation in the one router file modified post-scaffold; harmless, fixed with `ruff format`.

## Follow-ups

- Push on `Luna1xiao/bootstrap` and open the first PR (do not push to `main` directly).
- Ensure `backend/uv.lock` and `packages/shared-types/src/generated.ts` are committed — CI uses `uv sync --frozen` and UI imports the generated types.
- Notify each member of their module path and `AGENT.md`.
- Once 2–3 modules have real implementations, write the first cross-module integration test (subscribe → sync → clean → summarize).
