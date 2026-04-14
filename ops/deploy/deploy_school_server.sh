#!/usr/bin/env bash
# GOAT AI school Ubuntu deploy.
# Usage:
#   bash ops/deploy/deploy_school_server.sh
#   QUICK=1 bash ops/deploy/deploy_school_server.sh
#   SKIP_BUILD=1 bash ops/deploy/deploy_school_server.sh
#   SYNC_GIT=1 bash ops/deploy/deploy_school_server.sh

set -euo pipefail

_DEPLOY_SCRIPT="${BASH_SOURCE[0]:-$0}"
SCRIPT_DIR="$(cd "$(dirname "${_DEPLOY_SCRIPT}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "${SCRIPT_DIR}/../.." && pwd)}"
if [[ -f "$_DEPLOY_SCRIPT" ]]; then
  chmod +x "$_DEPLOY_SCRIPT" 2>/dev/null || true
fi
unset _DEPLOY_SCRIPT

PROJECT_DIR="${PROJECT_DIR:-$HOME/GOAT_AI}"
PRIMARY_DOTENV_PATH="${PROJECT_DIR}/.env"
SCHOOL_DOTENV_PATH="${PROJECT_DIR}/.env.school-ubuntu"
SCHOOL_LOCAL_OLLAMA_URL="${SCHOOL_LOCAL_OLLAMA_URL:-http://127.0.0.1:11435}"

GOAT_DEPLOY_MODE="${GOAT_DEPLOY_MODE:-1}"
if [ "${GOAT_DEPLOY_MODE}" != "1" ]; then
  echo "ops/deploy/deploy_school_server.sh requires GOAT_DEPLOY_MODE=1."
  exit 1
fi

DEPLOY_LABEL="GOAT AI school server deploy"
GOAT_SYSTEMD_UNIT="${GOAT_SYSTEMD_UNIT:-goat-ai.school-ubuntu}"

source "${SCRIPT_DIR}/lib/backend_server_deploy.sh"

GOAT_USE_SCHOOL_OLLAMA_LOCAL="${GOAT_USE_SCHOOL_OLLAMA_LOCAL:-}"
if [ -z "${GOAT_USE_SCHOOL_OLLAMA_LOCAL}" ]; then
  GOAT_USE_SCHOOL_OLLAMA_LOCAL="$(
    read_first_dotenv_value "GOAT_USE_SCHOOL_OLLAMA_LOCAL" "${SCHOOL_DOTENV_PATH}" "${PRIMARY_DOTENV_PATH}"
  )"
fi
GOAT_USE_SCHOOL_OLLAMA_LOCAL="${GOAT_USE_SCHOOL_OLLAMA_LOCAL:-1}"
GOAT_OLLAMA_PROFILE="${GOAT_OLLAMA_PROFILE:-$(
  read_first_dotenv_value "GOAT_OLLAMA_PROFILE" "${SCHOOL_DOTENV_PATH}" "${PRIMARY_DOTENV_PATH}"
)}"
GOAT_OLLAMA_PROFILE="${GOAT_OLLAMA_PROFILE:-school-ubuntu}"
if [ -z "${GOAT_BIND_HOST:-}" ]; then
  GOAT_BIND_HOST="$(
    read_first_dotenv_value "GOAT_BIND_HOST" "${SCHOOL_DOTENV_PATH}" "${PRIMARY_DOTENV_PATH}"
  )"
fi
GOAT_BIND_HOST="${GOAT_BIND_HOST:-0.0.0.0}"
if [ -z "${OLLAMA_BASE_URL:-}" ]; then
  OLLAMA_BASE_URL="$(
    read_first_dotenv_value "OLLAMA_BASE_URL" "${SCHOOL_DOTENV_PATH}" "${PRIMARY_DOTENV_PATH}"
  )"
fi
OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-${SCHOOL_LOCAL_OLLAMA_URL}}"

export GOAT_USE_SCHOOL_OLLAMA_LOCAL
export GOAT_OLLAMA_PROFILE
export GOAT_BIND_HOST
export OLLAMA_BASE_URL

goat_before_backend_start() {
  if [ ! -f "${PROJECT_DIR}/scripts/ollama/start_ollama_local.sh" ]; then
    echo "School server deploy requires ${PROJECT_DIR}/scripts/ollama/start_ollama_local.sh."
    exit 1
  fi

  echo "School Ubuntu Ollama profile enabled; ensuring local Ollama is running at ${OLLAMA_BASE_URL}"
  bash "${PROJECT_DIR}/scripts/ollama/start_ollama_local.sh"
}

goat_backend_server_deploy
