#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
WORKSPACE_ROOT="$(cd "${REPO_ROOT}/.." && pwd)"

OLLAMA_RUNTIME_DIR="${OLLAMA_RUNTIME_DIR:-${WORKSPACE_ROOT}/ollama-local}"
OLLAMA_HOST_VALUE="${OLLAMA_HOST:-http://127.0.0.1:11435}"
PID_FILE="${OLLAMA_RUNTIME_DIR}/run/ollama.pid"

echo "Host: ${OLLAMA_HOST_VALUE}"
echo "Runtime: ${OLLAMA_RUNTIME_DIR}"

if [ -f "${PID_FILE}" ]; then
  pid="$(cat "${PID_FILE}" 2>/dev/null || true)"
  echo "PID file: ${PID_FILE}"
  echo "PID: ${pid:-missing}"
  if [ -n "${pid}" ] && kill -0 "${pid}" 2>/dev/null; then
    echo "Process: running"
  else
    echo "Process: stale pidfile"
  fi
else
  echo "PID file: missing"
fi

if curl -sf "${OLLAMA_HOST_VALUE}/api/tags" >/dev/null 2>&1; then
  echo "HTTP: reachable"
  bash "${REPO_ROOT}/scripts/ollama/ollama_local.sh" list
else
  echo "HTTP: unreachable"
fi
