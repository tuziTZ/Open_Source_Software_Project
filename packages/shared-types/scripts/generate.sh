#!/usr/bin/env bash
# Regenerate TS types from the backend's OpenAPI schema.
#
# Usage:  pnpm gen:types
#
# Strategy: prefer a running backend on $MERCURY_PORT (default 8000). If none is
# reachable, boot uvicorn in the background for the duration of this script.

set -euo pipefail

PORT="${MERCURY_PORT:-8000}"
URL="http://127.0.0.1:${PORT}/openapi.json"
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
OUT="${REPO_ROOT}/packages/shared-types/src/generated.ts"
BACKEND_DIR="${REPO_ROOT}/backend"

cleanup() {
  if [[ -n "${UVICORN_PID:-}" ]]; then
    kill "${UVICORN_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

if ! curl -fsS "${URL}" > /dev/null 2>&1; then
  echo "No backend detected on :${PORT}; starting uvicorn temporarily..."
  (cd "${BACKEND_DIR}" && uv run uvicorn app.main:app --host 127.0.0.1 --port "${PORT}") &
  UVICORN_PID=$!
  for _ in $(seq 1 30); do
    sleep 0.5
    curl -fsS "${URL}" > /dev/null 2>&1 && break
  done
fi

echo "Fetching schema from ${URL}"
pnpm exec openapi-typescript "${URL}" -o "${OUT}"
echo "Wrote ${OUT}"
