#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
WORKSPACE_ROOT="$(cd "${REPO_ROOT}/.." && pwd)"

OLLAMA_RUNTIME_DIR="${OLLAMA_RUNTIME_DIR:-${WORKSPACE_ROOT}/ollama-local}"
OLLAMA_BASE_URL_VALUE="${OLLAMA_BASE_URL:-${OLLAMA_HOST:-http://127.0.0.1:11435}}"
PID_FILE="${OLLAMA_RUNTIME_DIR}/run/ollama.pid"
LOG_FILE="${OLLAMA_RUNTIME_DIR}/logs/ollama.log"

mkdir -p "${OLLAMA_RUNTIME_DIR}/run" "${OLLAMA_RUNTIME_DIR}/logs"

if curl -sf "${OLLAMA_BASE_URL_VALUE}/api/tags" >/dev/null 2>&1; then
  echo "Local Ollama already responding at ${OLLAMA_BASE_URL_VALUE}"
  exit 0
fi

if [ -f "${PID_FILE}" ]; then
  old_pid="$(cat "${PID_FILE}" 2>/dev/null || true)"
  if [ -n "${old_pid}" ] && kill -0 "${old_pid}" 2>/dev/null; then
    echo "Waiting for existing local Ollama process ${old_pid}..."
  else
    rm -f "${PID_FILE}"
  fi
fi

if [ ! -f "${PID_FILE}" ]; then
  echo "Starting local Ollama at ${OLLAMA_BASE_URL_VALUE}..."
  OLLAMA_HOST="${OLLAMA_BASE_URL_VALUE}" nohup bash "${REPO_ROOT}/scripts/ollama/ollama_local.sh" serve >>"${LOG_FILE}" 2>&1 &
  echo $! > "${PID_FILE}"
fi

for _ in $(seq 1 30); do
  if curl -sf "${OLLAMA_BASE_URL_VALUE}/api/tags" >/dev/null 2>&1; then
    echo "Local Ollama is ready at ${OLLAMA_BASE_URL_VALUE}"
    exit 0
  fi
  sleep 1
done

echo "Local Ollama did not become ready. Check ${LOG_FILE}"
exit 1
