# agent_summary — Agent Guide

**Owner**: member 6 (Summary Agent Engineer)

## Mission

Generate concise summaries of entries using an LLM. Support per-entry summaries and multi-entry digest summaries. Cache results so re-summarizing the same content does not re-spend tokens.

## Contract (HTTP)

Mounted at `/agents/summary`. Suggested endpoints:

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/agents/summary` | summarize one entry; body: `SummaryRequest` → `SummaryResult` |
| `POST` | `/agents/summary/digest` | summarize a set of entries into one digest |
| `GET` | `/agents/summary/{entry_id}` | fetch cached summary if present |

Use `app.schemas.SummaryRequest` and `app.schemas.SummaryResult`. Extend if needed and update `app/schemas/agent.py` so the contract stays single-source.

## Dependencies

- Imports `llm_providers` (NEVER call OpenAI/Ollama directly — go through the registry).
- May import `db` to persist results.
- Must NOT import other `agent_*` modules.
- Must NOT import `feed_engine` or `content_cleaner`.

## Non-Goals

- HTML cleaning (use already-cleaned `Entry.reader_html`).
- Translation (member 7).
- Provider selection logic (delegate to `llm_providers`).

## Acceptance Criteria

1. Long entries are chunked before sending to the LLM; chunks reassembled into one summary.
2. Same `(entry_id, provider, model, prompt_version)` returns the cached result without re-calling the LLM.
3. Failures return `LongTaskStatus = "failure"` with a clear error message; do not raise 500.
4. Token usage is recorded (will feed into the `UsageReport`).
5. Prompt template is versioned and referenced by version in the cache key.
6. `uv run pytest` and `uv run ruff check` pass.

## References

- `app/schemas/agent.py`
- `llm_providers/AGENT.md`
- `backend/AGENT.md`
