# content_cleaner completion

- Member: Kaleido66
- Date: 2026-06-02
- Agent: Claude Code
- Related PR: TBD

## Goal
Finalise the content cleaner module in `backend/content_cleaner/` so it meets all acceptance criteria in `AGENT.md`, is properly integrated with the DB storage contract, and passes full validation.

## Approach
The cleaning pipeline (`clean_html` and `clean_stored_article`) was already implemented in the prior session. This session focused on closing the remaining gaps:

- **Declared runtime dependencies** in `pyproject.toml`: `beautifulsoup4`, `lxml`, `bleach`, and `markdownify` were installed but not formally declared. Added them and ran `uv lock` to resolve the lock file.
- **Updated `README.md`** from the scaffold-era stub to a complete module reference covering the pipeline stages, public API, HTTP endpoints, DB hand-off contract, and test instructions.
- **Added integration tests** for `GET /content/entries/{id}/clean`: two new tests in `TestCleanStoredEndpoint` verify the end-to-end flow (mock DB reads → clean → mock DB write) and the edge case of an empty article body.

## Decisions
- Used `monkeypatch` for integration tests to mock `db.get_article_content`, `db.get_article`, and `db.save_article_content` inside `content_cleaner.service`, keeping tests fast and free of filesystem side effects. This follows the same pattern used by feed engine tests.
- Kept the existing `clean_stored_article` error-handling structure (catching `sqlite3.OperationalError` → 404) unchanged since the existing test suite validates it and altering error mapping is out of scope.
- Did not touch `packages/content-cleaner/` — the frontend package stub was removed as the cleaner engineer's remit is `backend/` only.

## Surprises
- `ruff` I001 (import order) required `import` statements before `from` imports inside function bodies — different from the module-level convention. Fixed by letting `ruff --fix` auto-sort.
- The `VIRTUAL_ENV` mismatch warning is a local environment issue (global Python 3.14 vs `.venv`); does not affect correctness.

## Verification

```bash
uv run ruff check content_cleaner/ tests/test_content_cleaner.py  # All checks passed
uv run pytest tests/test_content_cleaner.py -v                     # 32 passed
```

## Follow-ups
- The `GET /content/entries/{id}/clean` endpoint currently uses the default DB path only. Consider threading `db_path` through the service for testability without monkeypatch.
- Regenerate `packages/shared-types/src/generated.ts` to include `/content` paths once the frontend needs typed API access.
- Consider adding a `db_path` parameter to `clean_stored_article` for direct integration testing with `tmp_path`.
