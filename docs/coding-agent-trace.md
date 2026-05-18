# Coding Agent Trace

Assignment requirement #5: *form persistent, valuable working-process documentation*.

When you use a Coding Agent (Claude Code, Cursor, Copilot Chat, etc.) for a non-trivial change, commit a short log so the team can understand the reasoning later.

## Location

```
.agent-traces/
  YYYY-MM-DD-<member>-<topic>.md
```

Example: `.agent-traces/2026-05-20-tuziTZ-opml-import.md`

## Required Sections

```markdown
# <Topic>

- Member: <github handle>
- Date: <YYYY-MM-DD>
- Agent: <Claude Code / Cursor / ...>
- Related PR: <link or #number>

## Goal
One paragraph describing what you set out to do.

## Approach
The plan the agent suggested or you agreed on, including any options you rejected and why.

## Decisions
Choices that aren't obvious from the diff alone. Example: "Used `feedparser` over `defusedxml` because the team already had it in deps."

## Surprises
Anything unexpected — bugs found, dead ends, assumptions overturned.

## Follow-ups
TODOs the agent flagged that didn't make this PR.
```

## What NOT to Commit

- Raw transcripts (too noisy; the markdown summary is the artifact)
- Secrets, API keys, or private URLs
- Generated code dumps that are already in the diff

## Why This Matters

These logs feed two things:
1. Future code review — reviewers can understand *why* a non-obvious choice was made
2. The course deliverable — graders see the reasoning trail, not just the final diff

Keep each log under 300 words. Brevity > completeness.
