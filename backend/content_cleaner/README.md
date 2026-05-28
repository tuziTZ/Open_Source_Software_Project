# content_cleaner

Member 4's backend module for HTML cleaning and reader-mode content preparation.

## Purpose

This module will eventually clean raw article HTML, derive Markdown/plain text, and persist the result through `db.save_article_content(...)`.

## Current Shape

- HTTP router mounted at `/content`
- Module-local request/response models live in `schemas.py`
- Shared storage shape already exists in `app.schemas.content.ArticleContent`
- Service functions are stubbed so the integration points are in place

## Public API

```py
from content_cleaner.service import clean_html
from content_cleaner.schemas import CleanContentRequest

result = clean_html(
    CleanContentRequest(
        raw_html="<main><h1>Hello</h1></main>",
        source_url="https://example.com/article",
    )
)
```

## Database Hand-off

The cleaner is expected to:

1. read raw article content from `db.get_article_content(article_id)`
2. clean and normalize the HTML
3. write the result back with `db.save_article_content(...)`

The storage payload should include:

- `raw_html`
- `cleaned_html`
- `cleaned_markdown`
- `plain_text`
- `content_hash`

## Status

This is only a scaffold for now.

- no sanitizer or Markdown conversion yet
- no database write-back yet
- route signatures are in place for future implementation
