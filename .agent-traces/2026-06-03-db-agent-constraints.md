# DB Agent Constraints

- Member: storage engineer
- Date: 2026-06-03
- Agent: Codex
- Related PR: TBD

## Goal
Convert feedback from the weekly review into strict database-layer constraints for future teammates and Coding Agents.

## Approach
Update `backend/db/AGENT.md` with rules for search levels, SQLite FTS, future RAG boundaries, migration evolution, dependency/distribution risk, public API boundaries, testing commands, and Coding Agent trace requirements.

## Decisions
Keep the database core on stdlib `sqlite3` by default because Mercury is a cross-platform desktop app and dependency choices affect distribution. Treat RAG as a future optional module rather than a default storage dependency. Require new migrations instead of editing old merged migrations.

## Surprises
The existing `AGENT.md` was still an early scaffold and did not reflect the current storage API surface, FTS search, migration compatibility tests, or teammate usage rules.

## Follow-ups
Keep `backend/db/AGENT.md` and `backend/db/README.md` synchronized whenever repository APIs or migration policies change.
