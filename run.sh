#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
API_PORT="${NTT_API_PORT:-8080}"
WEB_PORT="${NTT_WEB_PORT:-5174}"

if [ ! -d "$ROOT/api/.venv" ]; then
  python3 -m venv "$ROOT/api/.venv"
  "$ROOT/api/.venv/bin/pip" install -r "$ROOT/api/requirements.txt"
fi
if [ ! -d "$ROOT/web/node_modules" ]; then
  (cd "$ROOT/web" && npm install)
fi

cleanup() {
  kill 0 2>/dev/null || true
}
trap cleanup EXIT

cd "$ROOT/api"
DATA_DIR="$ROOT/api/data" "$ROOT/api/.venv/bin/uvicorn" app.main:app --host 127.0.0.1 --port "$API_PORT" &
API_PID=$!

for i in $(seq 1 60); do
  if curl -sf "http://127.0.0.1:$API_PORT/healthz" >/dev/null; then
    break
  fi
  sleep 0.4
done

cd "$ROOT/web"
npm run dev -- --port "$WEB_PORT" --strictPort
wait "$API_PID"
