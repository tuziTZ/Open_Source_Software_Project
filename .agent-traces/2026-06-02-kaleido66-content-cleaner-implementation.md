# content_cleaner implementation

- Member: Kaleido66
- Date: 2026-06-02
- Agent: Claude Code
- Related PR: TBD

## Goal
Implement the full HTML cleaning pipeline for `backend/content_cleaner/`. The scaffold existed but `clean_html` and `clean_stored_article` both raised `NotImplementedError`. Needed to wire up sanitisation, Markdown conversion, URL resolution, and metadata computation so the module passes the 6 acceptance criteria in `AGENT.md`.

## Approach
Used a three-library stack: `beautifulsoup4`+`lxml` for parsing and DOM manipulation, `bleach` for allowlist-based sanitisation, and `markdownify` for HTML→Markdown conversion. Skipped `readability-lxml` because `feed_engine` already extracts article body content — the cleaner only receives the article HTML, not full web pages.

The pipeline runs: parse → bleach-sanitise → remove tracking pixels → resolve relative URLs → extract cleaned HTML / plain text → convert to Markdown → compute word count / reading time / SHA256 hash.

## Decisions
- Chose `bleach` allowlist over regex-based sanitisation for reliability against obfuscated XSS.
- Tracking pixel removal uses a heuristic (1×1 dimensions, `display:none`, suspicious src keywords) rather than a network-client blocklist, since network fetching is a non-goal.
- Content hash uses SHA256 of the *raw* HTML (before cleaning), truncated to 16 hex chars — deterministic and compact.
- Reading speed set at 200 WPM with a floor of 1 minute.

## Surprises
`markdownify` preserves code blocks and inline code well out of the box with `heading_style="ATX"`. The `bleach` allowlist needed careful tuning — allowing `class` on `<code>` and `<pre>` so syntax-highlighting hints survive, but stripping all `on*` event handlers by omission.

## Follow-ups
- Add integration tests for `GET /content/entries/{id}/clean` once a test database fixture is available.
- Consider a configurable reading-speed setting if the app gets user preferences.
