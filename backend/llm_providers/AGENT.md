# llm_providers — Agent Guide

**Owner**: member 8 (Platform Engineer)

## Mission

Abstract over LLM providers so summary/translation agents can stay provider-agnostic. Support any OpenAI-compatible HTTP endpoint and local models via Ollama. Configuration is persisted (the user adds providers via the settings UI, this module reads/writes that config).

## Contract (Python)

Suggested module layout:

```
llm_providers/
  __init__.py        re-exports the registry and Protocol
  base.py            LLMProvider protocol (chat, embeddings if needed)
  openai_compatible.py  generic client for any OpenAI-compatible API
  ollama.py          local provider
  registry.py        load_providers_from_config() / get_provider(name)
  config.py          provider config schema (Pydantic) + persistence
```

Public API:

```python
def get_provider(name: str | None = None) -> LLMProvider: ...
async def list_providers() -> list[ProviderConfig]: ...
async def add_provider(config: ProviderConfig) -> None: ...
```

The protocol must be small enough that adding a new provider is straightforward.

## Dependencies

- May add `httpx` (already a dev dep), `ollama-python` (optional).
- May import `db` if config is stored in SQLite, OR persist to a JSON file under `settings.data_dir`.
- Must NOT import `feed_engine`, `content_cleaner`, or `agent_*` (you are below them).
- Must NOT import FastAPI — this is a library.

## Non-Goals

- Prompt templates (live in `agent_summary/` and `agent_translation/`).
- Token accounting beyond raw usage numbers (aggregation is `db/`'s job).
- HTTP endpoints — if a provider config UI is needed, add a small router under `app/` not here.

## Acceptance Criteria

1. Adding a new OpenAI-compatible provider requires only a config entry, no code change.
2. Streaming responses supported (returns an async iterator of chunks).
3. Failures distinguish between auth, network, rate limit, and model errors.
4. At least one local (Ollama) and one cloud (OpenAI-compatible) provider tested with a mock server.
5. `uv run pytest` and `uv run ruff check` pass.

## References

- `app/schemas/agent.py` — request shapes carry optional `provider` and `model` overrides
- `backend/AGENT.md`
