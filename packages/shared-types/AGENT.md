# shared-types — Agent Guide

**Owner**: tech lead (member 1)

## Mission

Single source of TS type truth for the frontend. Generated from `backend`'s OpenAPI schema. Nobody edits `generated.ts` by hand.

## When to Touch This Package

- After changing any Pydantic model in `backend/app/schemas/` → run `pnpm gen:types`, commit the diff
- When adding a hand-written augmentation (utility type, narrowed union) → add a new file under `src/` and re-export from `src/index.ts`
- Never modify `src/generated.ts` directly

## Public API

```ts
import type { components, paths, operations } from "@mercury/shared-types";

type Feed = components["schemas"]["Feed"];
```

## Dependencies

- Dev only: `openapi-typescript`, `typescript`
- Requires `uv` + backend running for regeneration (`scripts/generate.sh` handles boot)

## Acceptance Criteria

1. `pnpm gen:types` produces a non-empty `generated.ts` whenever the backend has at least one Pydantic model.
2. `pnpm --filter ui typecheck` passes after regeneration.
3. The package exports only types, no runtime code.
