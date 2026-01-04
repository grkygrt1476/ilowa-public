#!/usr/bin/env bash
set -euo pipefail

API_URL=${API_URL:-http://localhost:8000/health}
MAX_RETRIES=${MAX_RETRIES:-60}
SLEEP_SECS=${SLEEP_SECS:-1}

for i in $(seq 1 "$MAX_RETRIES"); do
  if curl -fsS "$API_URL" > /dev/null 2>&1; then
    echo "[ok] api ready: $API_URL"
    exit 0
  fi
  sleep "$SLEEP_SECS"
done

echo "[fail] api not ready after ${MAX_RETRIES}s: $API_URL"
exit 1
