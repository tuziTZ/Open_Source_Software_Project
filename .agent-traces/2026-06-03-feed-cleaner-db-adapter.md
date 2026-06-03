# Feed Cleaner DB Adapter

- Member: storage engineer
- Date: 2026-06-03
- Agent: Codex
- Related PR: TBD

## Goal
Adapt the database layer to the real Feed Engine and Content Cleaner integration after remote updates landed.

## Approach
Inspect current schemas and cross-module imports, then preserve the existing Feed Engine contract by seeding `article_content.raw_html` from `Entry.reader_html` only when content does not already exist. Add `get_feed_sync_metadata()` so Feed Engine can read `etag` and `last_modified` without changing the public `Feed` schema.

## Decisions
Keep `Feed` unchanged to avoid OpenAPI/frontend type churn. Do not let later `save_article()` calls overwrite Cleaner-owned content fields. Document the Feed -> Cleaner compatibility contract in `backend/db/README.md` and `backend/db/AGENT.md`.

## Surprises
Feed Engine already sends parsed raw HTML through `Entry.reader_html`, while Cleaner expects it in `article_content.raw_html`; the database layer is the right adapter point.

## Follow-ups
Run Feed Engine, Content Cleaner, storage integration, and full backend tests before pushing.
