## Summary
<!-- One paragraph: what changed and why. -->

## Module
<!-- Which folder under backend/ or packages/ does this PR touch? -->
- [ ] `backend/feed_engine`
- [ ] `backend/db`
- [ ] `backend/content_cleaner`
- [ ] `backend/agent_summary`
- [ ] `backend/agent_translation`
- [ ] `backend/llm_providers`
- [ ] `backend/app` (tech lead)
- [ ] `packages/ui`
- [ ] `packages/shared-types` (tech lead)
- [ ] `packages/ipc-client` (tech lead)
- [ ] `apps/desktop`
- [ ] docs / CI / governance

## Checklist
- [ ] Tests added or updated
- [ ] `uv run ruff check` and `uv run pytest` pass locally (if backend)
- [ ] `pnpm typecheck` passes locally (if frontend)
- [ ] Pydantic model changed → ran `pnpm gen:types` and committed `packages/shared-types/src/generated.ts`
- [ ] New endpoint → updated `docs/ipc-contract.md`
- [ ] Coding Agent used → committed a trace under `.agent-traces/`

## Coding Agent Trace
<!-- Link to .agent-traces/YYYY-MM-DD-<member>-<topic>.md if applicable. -->

## Notes for Reviewers
<!-- Anything non-obvious; design choices; out-of-scope follow-ups. -->
