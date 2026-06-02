# content_cleaner

Member 4's backend module for HTML cleaning and reader-mode content preparation.

## Purpose

Converts raw article HTML into reader-friendly cleaned HTML and Markdown. Removes cruft (scripts, event handlers, tracking pixels) and derives plain text with reading metadata.

## Pipeline

The cleaning pipeline runs six stages:

1. **Parse** — `BeautifulSoup(lxml)` parses raw HTML
2. **Sanitise** — `bleach` allowlist strips `<script>`, inline `on*` handlers, `javascript:` URIs
3. **Remove trackers** — heuristic removal of 1×1 pixels, `display:none` images, and suspicious src paths
4. **Resolve URLs** — relative `href` / `src` are rewritten to absolute using the source URL as base
5. **Generate outputs** — cleaned HTML → plain text → Markdown (`markdownify`, ATX headings)
6. **Compute metadata** — word count, reading time (200 WPM floor 1 min), SHA-256 content hash (16 hex chars)

## Public API

```py
from content_cleaner.service import clean_html, clean_stored_article
from content_cleaner.schemas import CleanContentRequest

# Clean raw HTML directly
result = clean_html(
    CleanContentRequest(
        raw_html="<main><h1>Hello</h1></main>",
        source_url="https://example.com/article",
    )
)

# Clean a previously stored article (reads from DB, writes back)
result = clean_stored_article("article-001")
```

## HTTP Endpoints

Mounted at `/content` in [app/main.py](../app/main.py):

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/content/clean` | Clean raw HTML + source URL → cleaned HTML, Markdown, plain text, metadata |
| `GET` | `/content/entries/{id}/clean` | Clean an already-stored article by ID and persist the result |

## Database Hand-off

Follows the storage contract documented in [db/README.md](../db/README.md#cleaner-工程师示例):

1. Read raw content with `db.get_article_content(article_id)`
2. Clean and normalise the HTML
3. Write back with `db.save_article_content(...)` (upserts `article_content` and `article_search`)

Persisted fields:

- `raw_html` — original HTML (for hash comparison)
- `cleaned_html` — sanitised output (becomes `Entry.reader_html`)
- `cleaned_markdown` — Markdown rendering
- `plain_text` — full-text searchable body
- `content_hash` — SHA-256 truncated to 16 hex chars; used to skip re-cleaning unchanged articles

## Dependencies

Declared in [pyproject.toml](../pyproject.toml):

- `beautifulsoup4>=4.12` + `lxml>=5.3` — HTML parsing
- `bleach>=6.2` — allowlist-based sanitisation
- `markdownify>=1.1` — HTML → Markdown conversion

## Testing

```bash
uv run pytest tests/test_content_cleaner.py -v
```

Covers: typical blog posts, code-heavy articles, paywalled snippets, XSS sanitisation, URL resolution, word count / reading time, content hashing, and HTTP endpoints.

## Status

Implemented and passing all acceptance criteria from [AGENT.md](AGENT.md).
