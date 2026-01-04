#!/usr/bin/env bash
set -euo pipefail

API_URL=${API_URL:-http://localhost:8000/health}
PROOF_URL=${PROOF_URL:-http://localhost:8000/api/v1/jobs?per_page=3}

printf "[proof] health (%s)\n" "$API_URL"
curl -fsS "$API_URL" | head -c 800
printf "\n"

printf "[proof] sample (%s)\n" "$PROOF_URL"
curl -fsS "$PROOF_URL" | head -c 800
printf "\n"
