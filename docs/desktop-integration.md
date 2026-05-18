# Desktop Integration (Tauri + Python sidecar)

This document describes the recommended integration approach for the Mercury desktop application: a Tauri shell that hosts the `packages/ui` frontend and launches a Python FastAPI sidecar for business logic and LLM work.

## Goals

- Reuse `packages/ui` React app as the front-end inside a native shell.
- Keep business logic in Python `backend/` so agent work and local model usage remain in a mature ecosystem.
- Keep the app local-first, secure, and cross-platform.

## High-level architecture

- `packages/ui` (React/Vite) — front-end UI
- `backend/` (FastAPI) — sidecar process exposing HTTP endpoints (e.g. `/healthz`, `/agents/summary/generate`)
- `apps/desktop` (Tauri) — native shell that bundles the UI and the sidecar executable as a sidecar

## Dev workflow

1. Start the Python sidecar (development):

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

2. Start the UI dev server (another terminal):

```bash
pnpm --filter ui dev
```

3. In development the Tauri shell can be pointed at `http://127.0.0.1:5173` rather than bundling the production UI.

## Sidecar options

- HTTP (recommended): sidecar exposes a local HTTP port (easiest to debug and to generate types via OpenAPI).
- STDIN/STDOUT pipe: more secure (no HTTP port), but harder to implement concurrent requests and harder to debug.

## Packaging sidecar

- Use `PyInstaller` (or `nuitka`) to produce a platform-specific binary for the `backend/`.
- Add the produced binary as a `tauri.sidecar` in `tauri.conf.json` so Tauri can manage its lifecycle.

Example PyInstaller command:

```bash
cd backend
pip install pyinstaller
pyinstaller --onefile --name mercury_sidecar app/main.py
# Built binary: backend/dist/mercury_sidecar
```

## Security and binding

- Sidecar MUST bind to `127.0.0.1` only.
- Use a short-lived startup token or local socket file for the UI to authenticate to the sidecar if needed.

## Platform notes

- macOS: requires Xcode command line tools and notarization for published builds.
- Windows: requires Visual Studio build tools for building some Rust dependencies and proper handling of VC runtime for Python sidecar.
- Linux: needs `libwebkit2gtk` and other native deps.

## CI recommendations

- Use a matrix job for `ubuntu-latest`, `macos-latest`, `windows-latest`.
- Build the Python sidecar with PyInstaller on the corresponding OS runner and archive the binary as an artifact for Tauri to bundle.

## Minimal verification checklist

- [ ] UI dev + backend dev run concurrently and exchange a simple `/healthz` and `/agents/summary/generate` request.
- [ ] A PyInstaller-built sidecar runs locally and responds to `/healthz`.
- [ ] Tauri dev can start and connect to local dev backend.
- [ ] Tauri build can bundle the sidecar executable on the matching OS.

## Next steps

1. Implement a minimal `/agents/summary/generate` endpoint in `backend/` (a mock is fine for now).
2. Add `apps/desktop/tauri.conf.json` and a package.json for the desktop shell (this repo contains a minimal skeleton).
3. Add OpenAPI -> types generation to the dev workflow.


