#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
WORKSPACE_ROOT="$(cd "${REPO_ROOT}/.." && pwd)"

OLLAMA_RUNTIME_DIR="${OLLAMA_RUNTIME_DIR:-${WORKSPACE_ROOT}/ollama-local}"
OLLAMA_HOST_VALUE="${OLLAMA_HOST:-http://127.0.0.1:11435}"
PID_FILE="${OLLAMA_RUNTIME_DIR}/run/ollama.pid"

if [ ! -f "${PID_FILE}" ]; then
  echo "ℹ️ No local Ollama pidfile found."
  exit 0
fi

pid="$(cat "${PID_FILE}" 2>/dev/null || true)"
if [ -z "${pid}" ]; then
  rm -f "${PID_FILE}"
  echo "ℹ️ Removed empty pidfile."
  exit 0
fi

if kill -0 "${pid}" 2>/dev/null; then
  echo "🛑 Stopping local Ollama process ${pid}..."
  kill "${pid}" 2>/dev/null || true
  for _ in $(seq 1 10); do
    if ! kill -0 "${pid}" 2>/dev/null; then
      break
    fi
    sleep 1
  done
  if kill -0 "${pid}" 2>/dev/null; then
    kill -9 "${pid}" 2>/dev/null || true
  fi
fi

rm -f "${PID_FILE}"

if curl -sf "${OLLAMA_HOST_VALUE}/api/tags" >/dev/null 2>&1; then
  echo "⚠️ Local Ollama still answers on ${OLLAMA_HOST_VALUE}; another process may be serving."
else
  echo "✅ Local Ollama stopped."
fi
