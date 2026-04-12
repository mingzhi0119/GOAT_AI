#!/usr/bin/env bash
# Loop: healthcheck; optional QUICK deploy after N consecutive failures (GOAT_WATCHDOG_RESTART=1).
# Run inside tmux on servers without systemd user session.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$HOME/GOAT_AI}"
FAIL_THRESHOLD="${GOAT_WATCHDOG_FAIL_THRESHOLD:-3}"
SLEEP_SEC="${GOAT_WATCHDOG_SLEEP_SEC:-60}"
LOG="${GOAT_WATCHDOG_LOG:-$PROJECT_DIR/logs/watchdog.log}"
mkdir -p "$(dirname "$LOG")"
fail_count=0
while true; do
  if bash "$SCRIPT_DIR/healthcheck.sh"; then
    fail_count=0
  else
    fail_count=$((fail_count + 1))
    echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") health failed ($fail_count/$FAIL_THRESHOLD)" >> "$LOG"
    if [ "$fail_count" -ge "$FAIL_THRESHOLD" ] && [ "${GOAT_WATCHDOG_RESTART:-0}" = "1" ]; then
      echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") restarting via deploy.sh (QUICK=1)" >> "$LOG"
      (cd "$PROJECT_DIR" && QUICK=1 bash deploy.sh) >> "$LOG" 2>&1 || true
      fail_count=0
    fi
  fi
  sleep "$SLEEP_SEC"
done
