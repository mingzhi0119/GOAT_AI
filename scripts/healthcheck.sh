#!/usr/bin/env bash
# Curl FastAPI /api/health; exit 1 on failure (for cron or watchdog).
set -euo pipefail
: "${GOAT_HEALTH_URL:=http://127.0.0.1:62606/api/health}"
curl -sf "$GOAT_HEALTH_URL" >/dev/null
