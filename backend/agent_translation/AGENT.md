# agent_translation — Agent Guide

**Owner**: member 7 (Translation Agent Engineer)

## Mission

Translate entry content using an LLM. Support multiple modes (full translation, bilingual side-by-side) and language detection. Cache results.

## Contract (HTTP)

Mounted at `/agents/translation`. Suggested endpoints:

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/agents/translation` | translate one entry; body: `TranslationRequest` → `TranslationResult` |
| `GET` | `/agents/translation/{entry_id}?lang=...` | fetch cached translation |
| `POST` | `/agents/translation/detect` | language detection only |

Use `app.schemas.TranslationRequest` and `app.schemas.TranslationResult`. Extend if needed and update `app/schemas/agent.py`.

## Dependencies

- Imports `llm_providers` (never call providers directly).
- May import `db` to persist results.
- Must NOT import other `agent_*`, `feed_engine`, or `content_cleaner`.

## Non-Goals

- Summarization (member 6).
- Provider selection (delegate to `llm_providers`).

## Acceptance Criteria

1. Bilingual mode aligns source and translated paragraphs in the returned HTML structure.
2. Same `(entry_id, target_lang, provider, model, prompt_version)` returns cached result.
3. Skips translation when source language equals target language; returns the source as-is with a status note.
4. Failures return `LongTaskStatus = "failure"` with a clear error message; do not raise 500.
5. Token usage recorded.
6. `uv run pytest` and `uv run ruff check` pass.

## References

- `app/schemas/agent.py`
- `app/schemas/entry.py` — `translation_html` and `translation_status` fields
- `llm_providers/AGENT.md`
- `backend/AGENT.md`
