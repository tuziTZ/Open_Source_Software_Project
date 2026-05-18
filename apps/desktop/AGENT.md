# apps/desktop — Agent Guide

**Owner**: member 8 (Platform Engineer)

## Mission

Wrap `packages/ui` in a cross-platform Tauri shell, manage the Python sidecar lifecycle, and produce platform-specific installers for Windows / macOS / Linux.

This folder is empty by design — the tech lead does not pre-scaffold Rust code. Member 8 owns the first commit here.

## What to Build

1. **Tauri project under `src-tauri/`** (use `pnpm create tauri-app` or initialize manually)
   - `Cargo.toml` with `tauri` v2 deps
   - `tauri.conf.json` configured to:
     - Load the built UI from `../../../packages/ui/dist`
     - Declare the Python sidecar binary
     - Set window title, icon, identifiers
   - `src/main.rs` that:
     - Picks a free localhost port at boot
     - Spawns the Python sidecar with `MERCURY_PORT=<that port>`
     - Injects `window.__BACKEND_PORT__ = <port>` into the webview via `initialization_script`
     - Kills the sidecar on window close

2. **`apps/desktop/package.json`** with scripts: `dev`, `build`, `tauri`

3. **Sidecar packaging**
   - Use PyInstaller to bundle `backend/app/main.py` into a single binary per platform
   - Place outputs in `src-tauri/binaries/` with names like `mercury-backend-x86_64-apple-darwin`
   - Tauri's sidecar feature picks them up by platform triple

4. **Dev workflow**
   - `pnpm --filter desktop dev` runs `tauri dev`, which spawns the Python sidecar from `backend/` (no need to bundle in dev)
   - Production builds bundle the PyInstaller artifact

## Dependencies

- Reads from `packages/ui/dist` (built first)
- Reads from `backend/` (Python source for dev, PyInstaller binary for prod)
- Coordinates with the tech lead on the `__BACKEND_PORT__` injection contract

## Non-Goals

- Writing UI code (member 5)
- Writing backend code (other members)
- Auto-update infrastructure for v1 — local-first; users update by reinstalling

## Acceptance Criteria

1. `pnpm --filter desktop dev` opens a window showing the UI; UI can fetch `/healthz` successfully.
2. Production build (`pnpm --filter desktop build`) produces a runnable installer on macOS, Windows, and Linux.
3. Closing the window terminates the Python sidecar process — no orphan processes.
4. Sidecar port collision is impossible (use port 0 + `getsockname`).
5. CI workflow (extended by member 9) builds the desktop app on all three platforms.

## References

- [Tauri sidecar docs](https://v2.tauri.app/develop/sidecar/)
- [PyInstaller](https://pyinstaller.org/)
- `docs/architecture.md` — process model section
- `backend/app/config.py` — `MERCURY_PORT` env var contract
