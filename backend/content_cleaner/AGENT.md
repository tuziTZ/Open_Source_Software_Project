# content_cleaner — Agent Guide

**Owner**: member 4 (Content Cleaner Engineer)

## Mission

Convert raw entry HTML into reader-friendly cleaned HTML and Markdown. Apply consistent styling and remove cruft (ads, trackers, navigation chrome).

## Contract (HTTP)

Mounted at `/content`. Suggested endpoints:

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/content/clean` | input: raw HTML + source URL → output: cleaned HTML + Markdown + reading metadata |
| `GET` | `/content/entries/{id}/clean` | clean an already-stored entry by id |

Define request/response models inside this module (e.g. `content_cleaner/schemas.py`) since they are module-specific. The cleaned output should populate `Entry.reader_html` when persisted.

## Dependencies

- May import from `db` (read raw entries, store cleaned output).
- May add libraries via `pyproject.toml` (suggest `readability-lxml`, `beautifulsoup4`, `bleach`, `markdownify`).
- Must NOT import `feed_engine` or any `agent_*` module.

## Non-Goals

- Network fetching (that's `feed_engine`).
- Summary or translation (those are `agent_*`).

## Acceptance Criteria

1. Output HTML passes a sanitizer allowlist (no `<script>`, no inline event handlers, no remote tracking pixels).
2. Markdown output preserves headings, lists, links, code blocks, blockquotes.
3. Relative URLs are resolved against the source URL.
4. Reading time and word count metadata included in the response.
5. Tests cover at least: a typical blog post, a code-heavy post, and a paywalled snippet.
6. `uv run pytest` and `uv run ruff check` pass.

## References

- `app/schemas/entry.py` — `reader_html` field consumes the cleaned output
- `backend/AGENT.md` — workspace-level rules
