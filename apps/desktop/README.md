# Desktop Shell

`apps/desktop` is the Tauri packaging entry for the Lumen desktop app.

## Layout

- `package.json`: Tauri CLI scripts
- `tauri.conf.json`: bundle config, UI dist wiring, installer target selection
- `Cargo.toml`, `build.rs`, `src/`: Rust shell that starts the backend and injects `window.__BACKEND_PORT__`
- `scripts/prepare-build.mjs`: production build prep for UI assets and backend sidecar invocation
- `icons/`: bundled app icons

## Build flow

1. `pnpm --filter desktop build`
2. Dev mode runs `node ./scripts/start-ui-dev.mjs`
3. Production build runs `node ./scripts/prepare-build.mjs`
4. The build script resolves a working `pnpm` executable and builds `packages/ui`
5. The build script calls `backend/scripts/build_sidecar.py`
6. The backend script creates or reuses `backend/.venv-sidecar`, installs desktop packaging deps, and bundles `backend/run_sidecar.py`
7. Tauri maps `backend/dist/mercury-backend(.exe)` into the packaged app as `binaries/mercury-backend(.exe)`
8. Tauri bundles the Rust shell plus the generated backend binary into an NSIS installer

## macOS packaging

- A real `.app` / `.dmg` must be built on macOS. Windows cannot produce a notarizable or runnable macOS bundle directly.
- On a Mac, run `pnpm --filter desktop build:mac`.
- In CI, trigger `.github/workflows/desktop-macos.yml` to produce downloadable macOS artifacts.
- The macOS build generates `apps/desktop/icons/icon.icns` from [icon.png](/d:/githubcode/Open_Source_Software_Project/apps/desktop/icons/icon.png) before bundling.

## Notes

- Development mode does not bundle the backend. The Rust shell starts FastAPI directly from `backend/`.
- Production mode expects the packaged backend binary under `resource_dir/binaries/`.
- If you change backend startup behavior, update both `backend/run_sidecar.py` and `src/main.rs`.

## Install And Smoke Test

Build the installer:

```bash
pnpm --filter desktop build
```

Installer output:

- [Lumen Desktop_0.1.0_x64-setup.exe](</d:/githubcode/Open_Source_Software_Project/apps/desktop/target/release/bundle/nsis/Lumen Desktop_0.1.0_x64-setup.exe>)

Quick manual test after installation:

1. Open Lumen.
2. Click `Import OPML...`.
3. Choose [mercury-demo.opml](/d:/githubcode/Open_Source_Software_Project/docs/examples/mercury-demo.opml).
4. Keep `Sync Now` enabled and continue.
5. Open any imported article and click `Summary`.

Feed URL alternative:

- `https://devblogs.microsoft.com/python/feed/`

Summary mode:

- Without `LLM_API_KEY`, the backend falls back to mock summaries so the click-flow remains testable.
- For a real model, set `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, and `LLM_USE_MOCK=false` before launching the app.
- Desktop builds also read `%USERPROFILE%\\.mercury\\agent_summary.env` and `%USERPROFILE%\\.mercury\\.env`, so you can persist model config there for installed builds.
