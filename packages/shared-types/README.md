# @mercury/shared-types

Auto-generated TypeScript types from the FastAPI backend's OpenAPI schema. Imported by `packages/ui` and `packages/ipc-client`.

## Regenerate

```bash
pnpm gen:types
```

This runs `scripts/generate.sh`, which:
1. Checks for a running backend on `127.0.0.1:8000`
2. If none is running, boots `uvicorn app.main:app` for the duration of the script
3. Fetches `/openapi.json`
4. Pipes it through `openapi-typescript` into `src/generated.ts`

## When to Regenerate

Whenever the backend changes:
- A new Pydantic model in `backend/app/schemas/`
- A new field on an existing model
- A new or modified route signature
- A removed or renamed endpoint

Commit the updated `src/generated.ts` in the same PR as the backend change.

## Do Not Edit `generated.ts` by Hand

It is overwritten on every regeneration. Add hand-written augmentations (utility types, narrowed unions) in separate files under `src/` and re-export from `src/index.ts`.
