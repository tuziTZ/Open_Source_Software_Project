# ipc-client — Agent Guide

**Owner**: tech lead (member 1) — extended by feature owners as endpoints land.

## Mission

Provide a small, typed `fetch` wrapper for the frontend to call the Python backend. Returns parsed JSON or throws `IpcError`. Each module owner adds typed wrapper functions for their own endpoints in separate files under `src/`.

## Public API

```ts
import { createClient, IpcError } from "@mercury/ipc-client";

const client = createClient({ baseUrl: "http://127.0.0.1:8000" });

const feeds = await client.request<Feed[]>("GET", "/feeds");
```

## When to Add Endpoint Wrappers

When you implement a new backend endpoint, add a typed wrapper:

```ts
// src/feeds.ts
import type { components } from "@mercury/shared-types";
import type { IpcClient } from "./index";

export const syncFeed = (client: IpcClient, id: string) =>
  client.request<components["schemas"]["Feed"]>("POST", `/feeds/${id}/sync`);
```

Re-export from `src/index.ts`. This keeps the type linkage between `shared-types` and call sites compile-time enforced.

## Acceptance Criteria

1. `createClient` works in both Node (for tests) and browser (in `packages/ui`).
2. Errors carry HTTP status, URL, and parsed body.
3. No runtime dependency except `fetch`. No transitive bundles.
