#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
WORKSPACE_ROOT="$(cd "${REPO_ROOT}/.." && pwd)"

OLLAMA_INSTALL_DIR="${OLLAMA_INSTALL_DIR:-${WORKSPACE_ROOT}/ollama}"
OLLAMA_RUNTIME_DIR="${OLLAMA_RUNTIME_DIR:-${WORKSPACE_ROOT}/ollama-local}"
OLLAMA_HOST_VALUE="${OLLAMA_HOST:-http://127.0.0.1:11435}"

BIN_CANDIDATES=(
  "${OLLAMA_RUNTIME_DIR}/bin/ollama"
  "${OLLAMA_INSTALL_DIR}/bin/ollama"
)

find_ollama_bin() {
  local candidate
  for candidate in "${BIN_CANDIDATES[@]}"; do
    if [ -x "${candidate}" ]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done
  return 1
}

OLLAMA_BIN="$(find_ollama_bin || true)"
if [ -z "${OLLAMA_BIN}" ]; then
  echo "❌ Could not find a local Ollama binary in ${OLLAMA_RUNTIME_DIR}/bin or ${OLLAMA_INSTALL_DIR}/bin."
  exit 1
fi

mkdir -p \
  "${OLLAMA_RUNTIME_DIR}/bin" \
  "${OLLAMA_RUNTIME_DIR}/home/.ollama" \
  "${OLLAMA_RUNTIME_DIR}/lib/ollama" \
  "${OLLAMA_RUNTIME_DIR}/logs" \
  "${OLLAMA_RUNTIME_DIR}/models" \
  "${OLLAMA_RUNTIME_DIR}/run"

if [ ! -x "${OLLAMA_RUNTIME_DIR}/bin/ollama" ] && [ "${OLLAMA_BIN}" != "${OLLAMA_RUNTIME_DIR}/bin/ollama" ]; then
  ln -sf "${OLLAMA_BIN}" "${OLLAMA_RUNTIME_DIR}/bin/ollama"
fi

export HOME="${OLLAMA_RUNTIME_DIR}/home"
export OLLAMA_HOST="${OLLAMA_HOST_VALUE}"
export OLLAMA_MODELS="${OLLAMA_RUNTIME_DIR}/models"
export PATH="${OLLAMA_RUNTIME_DIR}/bin:${OLLAMA_INSTALL_DIR}/bin:${PATH}"
export LD_LIBRARY_PATH="${OLLAMA_RUNTIME_DIR}/lib/ollama:${OLLAMA_INSTALL_DIR}/lib/ollama:${LD_LIBRARY_PATH:-}"

exec "${OLLAMA_BIN}" "$@"
