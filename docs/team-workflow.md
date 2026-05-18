# Team Workflow

## Roles

| # | Role | Module |
|---|---|---|
| 1 | Tech Lead / Integrator | `backend/app/`, `packages/shared-types`, `packages/ipc-client`, `docs/`, `.github/` |
| 2 | Feed Engineer | `backend/feed_engine/` |
| 3 | Storage Engineer | `backend/db/` |
| 4 | Content Cleaner Engineer | `backend/content_cleaner/` |
| 5 | UI Engineer | `packages/ui/` |
| 6 | Summary Agent Engineer | `backend/agent_summary/` |
| 7 | Translation Agent Engineer | `backend/agent_translation/` |
| 8 | Platform Engineer | `apps/desktop/`, `backend/llm_providers/` |
| 9 | QA / DevOps / Docs | `.github/workflows/`, `docs/`, cross-module tests |

GitHub usernames: see `docs/team.md`.

## Branch Strategy

- `main` is the integration branch. Always green.
- Each feature ships from a short-lived feature branch named `<member>/<topic>`, e.g. `tuziTZ/feed-opml-import`.
- Open a PR against `main` when ready. Squash-merge on approval.
- Do not push directly to `main`.

## Commit Messages

```
<module>: <short imperative>

<optional body — why, not what>
```

Examples:
- `feed_engine: add OPML nested outline parsing`
- `db: introduce entries table with FK to feeds`
- `app: expose /healthz`

Use lowercase module name matching the folder. The module prefix makes git log scannable per owner.

## Pull Requests

Every PR must:
1. Touch exactly one module (rare exceptions: integration PRs by the tech lead).
2. Use the PR template (`.github/pull_request_template.md`).
3. Have CI green.
4. Have at least one review from the module owner OR the tech lead.
5. If it changes any Pydantic model or route signature, include the regenerated `packages/shared-types/src/generated.ts`.

Cross-module changes (e.g. `feed_engine` needs a new field on `Entry`) require two PRs in order:
1. Tech lead updates `app/schemas/entry.py`, regenerates types, merges.
2. Feature owner uses the new field, merges.

## Code Review

- **Module owner** reviews changes to their own module.
- **Tech lead** reviews any change to `backend/app/`, `packages/shared-types`, `packages/ipc-client`, `docs/`, or `.github/`.
- `CODEOWNERS` auto-assigns reviewers.

What reviewers check:
- Public API matches the AGENT.md contract
- New endpoints documented in `docs/ipc-contract.md`
- Tests included for new behavior
- No leaking abstractions (e.g. SQL rows escaping `db/`)
- Lint + typecheck pass locally

## Integration Cadence

- Daily: tech lead skims open PRs, unblocks merge conflicts
- Weekly: integration call (30 min) — owners demo what landed, surface blockers
- Pre-release: tech lead runs end-to-end smoke (UI → backend → DB → LLM)

## Coding Agent Trace (assignment requirement #5)

Every member who uses a Coding Agent (Claude Code, Cursor, Copilot Chat, etc.) for a non-trivial change must commit a session log under `.agent-traces/`. See `docs/coding-agent-trace.md` for the format.

## Local Development

```bash
# Install JS deps (root)
pnpm install

# Install Python deps
cd backend && uv sync

# Start backend
uv run uvicorn app.main:app --reload

# Start UI (another terminal)
pnpm --filter ui dev

# Regenerate TS types after backend changes
pnpm gen:types

# Lint + typecheck + test (everything)
pnpm typecheck
cd backend && uv run pytest && uv run ruff check
```
