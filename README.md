# 小组成员github账户



| 姓名           | 账户                                 |
| -------------- | ------------------------------------ |
| 萧海玥（组长） | https://github.com/Luna1xiao/        |
| 彭一珅         | https://github.com/tuziTZ            |
| 刘蔚美         | https://github.com/Annie191          |
| 王瑞彬         | https://github.com/Kaleido66         |
| 杭东升         | https://github.com/ddsplus           |
| 赵欣雨         | https://github.com/YWDJ123           |
| 吴天辰         | https://github.com/jiaotangbuding177 |
| 徐晨           | https://github.com/OrangerXu         |
| 屠恒彦         | https://github.com/hengyantu         |

# Lumen

A local-first, cross-platform RSS reader with AI-assisted summarization and translation. Built as a course project for the Open-Source Software class.

Team: see [`docs/team.md`](docs/team.md).

## Stack

- **Frontend**: React 19 + Vite + TypeScript (`packages/ui`)
- **Backend**: Python 3.11+ + FastAPI + SQLite (`backend/`)
- **Desktop shell**: Tauri (`apps/desktop/`)
- **Type contract**: Pydantic → OpenAPI → `openapi-typescript` → `packages/shared-types`
- **Tooling**: pnpm workspaces, `uv` for Python deps

See [`docs/architecture.md`](docs/architecture.md) for the full picture.

## Prerequisites

- Node.js 20+
- pnpm 10+ (`corepack enable && corepack prepare pnpm@10.11.0 --activate`)
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`

## Setup

```bash
# 1. Install JS deps (root)
pnpm install

# 2. Install Python deps
cd backend && uv sync && cd ..
```

## Development

Run backend and frontend in two terminals:

```bash
# Terminal 1 — backend on :8000
pnpm dev:backend

# Terminal 2 — UI dev server on :5173
pnpm dev:ui
```

Open `http://127.0.0.1:5173`. The UI talks to the backend at `http://127.0.0.1:8000`.

Backend health check: `http://127.0.0.1:8000/healthz`
OpenAPI docs: `http://127.0.0.1:8000/docs`

## Regenerating TypeScript Types from the Backend

```bash
pnpm gen:types
```

Run this whenever a Pydantic model in `backend/app/schemas/` or a route signature changes. Commit the regenerated `packages/shared-types/src/generated.ts` in the same PR.

## Running Tests and Lint

```bash
# JS / TS
pnpm typecheck
pnpm test

# Python
cd backend
uv run pytest
uv run ruff check
```

## Repository Layout

```
.
├── apps/
│   └── desktop/         Tauri shell (member 8)
├── backend/             Python FastAPI sidecar
│   ├── app/             composition root + Pydantic schemas (tech lead)
│   ├── feed_engine/     RSS/Atom/OPML
│   ├── db/              SQLite + repositories
│   ├── content_cleaner/ HTML cleaning + Markdown
│   ├── agent_summary/   summary agent
│   ├── agent_translation/ translation agent
│   └── llm_providers/   provider abstractions
├── packages/
│   ├── ui/              React frontend
│   ├── shared-types/    generated TS contract
│   └── ipc-client/      typed fetch wrapper
├── docs/                architecture, workflow, contract, team
└── .github/             CI, PR template, CODEOWNERS
```

Each module has its own `AGENT.md` describing scope, contract, and acceptance criteria.

## Documentation

- [`docs/architecture.md`](docs/architecture.md) — process model, layering, data flow
- [`docs/team-workflow.md`](docs/team-workflow.md) — branches, PRs, reviews
- [`docs/ipc-contract.md`](docs/ipc-contract.md) — endpoint table and breaking-change policy
- [`docs/coding-agent-trace.md`](docs/coding-agent-trace.md) — how to log Coding Agent sessions
- [`docs/team.md`](docs/team.md) — members and modules
