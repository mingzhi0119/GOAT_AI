#!/usr/bin/env bash
# GOAT AI production deploy (FastAPI + React on :62606)
# Usage:
#   bash deploy.sh                   # full deploy from current local working tree
#   QUICK=1 bash deploy.sh           # quick restart: skip pip install
#   SKIP_BUILD=1 bash deploy.sh      # skip npm build (use existing dist/)
#   SYNC_GIT=1 bash deploy.sh        # sync and deploy the exact requested branch/ref
#   GIT_REF=<ref> bash deploy.sh     # deploy a specific branch, tag, or commit
#   RELEASE_BUNDLE=/tmp/goat-release.tar.gz RELEASE_MANIFEST=/tmp/release-manifest.json bash deploy.sh
#
# Override any variable before running, for example:
#   GOAT_SERVER_PORT=62606 bash deploy.sh

_DEPLOY_SCRIPT="${BASH_SOURCE[0]:-$0}"
SCRIPT_DIR="$(cd "$(dirname "${_DEPLOY_SCRIPT}")" && pwd)"
if [[ -f "$_DEPLOY_SCRIPT" ]]; then
  chmod +x "$_DEPLOY_SCRIPT" 2>/dev/null || true
fi
unset _DEPLOY_SCRIPT

set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/mingzhi0119/GOAT_AI.git}"
PROJECT_DIR="${PROJECT_DIR:-$HOME/GOAT_AI}"
GIT_BRANCH="${GIT_BRANCH:-main}"
GIT_REF="${GIT_REF:-$GIT_BRANCH}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-$PROJECT_DIR/.venv}"

LOCAL_OLLAMA_URL="${LOCAL_OLLAMA_URL:-http://127.0.0.1:11435}"
SERVER_PORT="${GOAT_SERVER_PORT:-62606}"
EFFECTIVE_OLLAMA_URL="${OLLAMA_BASE_URL:-${LOCAL_OLLAMA_URL}}"

RELEASE_BUNDLE="${RELEASE_BUNDLE:-}"
RELEASE_MANIFEST="${RELEASE_MANIFEST:-}"
SKIP_BUILD="${SKIP_BUILD:-}"
QUICK="${QUICK:-0}"
SYNC_GIT="${SYNC_GIT:-0}"
EXPECTED_GIT_SHA="${EXPECTED_GIT_SHA:-}"
BUNDLE_DEPLOY=0

if [ -n "${RELEASE_BUNDLE}" ]; then
  BUNDLE_DEPLOY=1
  : "${SKIP_BUILD:=1}"
else
  : "${SKIP_BUILD:=0}"
fi

echo "GOAT AI deploy starting (branch: ${GIT_BRANCH}, ref: ${GIT_REF})${QUICK:+ [QUICK mode]}"

free_port() {
  local p="$1"
  if command -v fuser >/dev/null 2>&1; then
    fuser -k "${p}/tcp" 2>/dev/null || true
  elif command -v lsof >/dev/null 2>&1; then
    local pids
    pids=$(lsof -ti ":${p}" 2>/dev/null || true)
    [ -n "$pids" ] && echo "$pids" | xargs -r kill -9 2>/dev/null || true
  fi
  sleep 1
}

healthcheck_port() {
  local p="$1"
  for _ in {1..15}; do
    if curl -sf "http://127.0.0.1:${p}/api/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

wait_for_pid_exit() {
  local pid="$1"
  local max_wait_sec="${2:-30}"
  for _ in $(seq 1 "${max_wait_sec}"); do
    if ! kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
    sleep 1
  done
  return 1
}

stop_pidfile() {
  local pidfile="$1"
  if [ -f "$pidfile" ]; then
    local old_pid
    old_pid="$(cat "$pidfile" 2>/dev/null || true)"
    if [ -n "$old_pid" ] && kill -0 "$old_pid" 2>/dev/null; then
      kill "$old_pid" 2>/dev/null || true
      if ! wait_for_pid_exit "$old_pid" 30; then
        echo "Graceful shutdown timed out for PID ${old_pid}; forcing cleanup."
        kill -9 "$old_pid" 2>/dev/null || true
      fi
    fi
    rm -f "$pidfile"
  fi
}

verify_expected_git_sha() {
  if [ "${BUNDLE_DEPLOY}" = "1" ]; then
    return 0
  fi
  local current_sha
  current_sha="$(git rev-parse HEAD)"
  if [ -n "${EXPECTED_GIT_SHA}" ] && [ "${current_sha}" != "${EXPECTED_GIT_SHA}" ]; then
    echo "Resolved SHA ${current_sha} did not match EXPECTED_GIT_SHA ${EXPECTED_GIT_SHA}"
    exit 1
  fi
}

sync_requested_ref() {
  git fetch --all --prune --tags
  if git show-ref --verify --quiet "refs/remotes/origin/${GIT_REF}"; then
    echo "Syncing branch ref to origin/${GIT_REF}"
    git checkout --detach "origin/${GIT_REF}"
    git reset --hard "origin/${GIT_REF}"
  else
    local resolved_sha
    resolved_sha="$(git rev-parse --verify "${GIT_REF}^{commit}")"
    echo "Syncing immutable ref ${GIT_REF} (${resolved_sha})"
    git checkout --detach "${resolved_sha}"
    git reset --hard "${resolved_sha}"
  fi
  verify_expected_git_sha
}

echo "1. Project checkout"
if [ "${BUNDLE_DEPLOY}" = "1" ]; then
  if [ -z "${RELEASE_MANIFEST}" ]; then
    echo "RELEASE_MANIFEST is required when RELEASE_BUNDLE is set."
    exit 1
  fi
  echo "Installing immutable release bundle into ${PROJECT_DIR}"
  mkdir -p "${PROJECT_DIR}"
  _previous_release_manifest=""
  if [ -f "${PROJECT_DIR}/release-manifest.json" ]; then
    _previous_release_manifest="$(mktemp)"
    cp "${PROJECT_DIR}/release-manifest.json" "${_previous_release_manifest}"
  fi
  "${PYTHON_BIN}" "${SCRIPT_DIR}/tools/install_release_bundle.py" \
    --bundle "${RELEASE_BUNDLE}" \
    --manifest "${RELEASE_MANIFEST}" \
    --project-dir "${PROJECT_DIR}" \
    --expected-sha "${EXPECTED_GIT_SHA}"
  if [ -n "${_previous_release_manifest}" ]; then
    cp "${_previous_release_manifest}" "${PROJECT_DIR}/release-manifest.previous.json"
    rm -f "${_previous_release_manifest}"
  fi
  cp "${RELEASE_MANIFEST}" "${PROJECT_DIR}/release-manifest.json"
else
  if [ ! -d "${PROJECT_DIR}/.git" ]; then
    echo "Cloning repository"
    git clone "$REPO_URL" "$PROJECT_DIR"
  fi

  cd "$PROJECT_DIR"

  if [ "${SYNC_GIT}" = "1" ]; then
    sync_requested_ref
    echo "Repository synced to $(git rev-parse HEAD)"
  else
    git checkout "$GIT_REF"
    verify_expected_git_sha
    echo "Deploying current local checkout for ref ${GIT_REF} (SYNC_GIT=0)"
  fi
fi

cd "$PROJECT_DIR"

# Re-derive EFFECTIVE_OLLAMA_URL from project .env when not already set in shell,
# so deploy skips local-Ollama startup when OLLAMA_BASE_URL is configured there.
if [ -z "${OLLAMA_BASE_URL:-}" ] && [ -f "${PROJECT_DIR}/.env" ]; then
  _dotenv_ollama="$(grep -m1 '^OLLAMA_BASE_URL=' "${PROJECT_DIR}/.env" 2>/dev/null | cut -d= -f2- | tr -d "'\"")"
  if [ -n "$_dotenv_ollama" ]; then
    OLLAMA_BASE_URL="$_dotenv_ollama"
    EFFECTIVE_OLLAMA_URL="$_dotenv_ollama"
  fi
fi

echo "2. Python virtualenv and dependencies"
if [ "${QUICK}" = "1" ]; then
  echo "[QUICK] Skipping Python venv and pip install"
  if [ ! -x "${VENV_DIR}/bin/python" ]; then
    echo "Venv not found at ${VENV_DIR}. Run a full deploy first."
    exit 1
  fi
else
  if [ ! -x "${VENV_DIR}/bin/python" ]; then
    echo "Creating virtualenv at ${VENV_DIR}"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
  fi

  echo "Installing Python dependencies"
  "${VENV_DIR}/bin/pip" install --upgrade pip --quiet
  "${VENV_DIR}/bin/pip" install -r requirements.txt --quiet
  echo "Python dependencies installed"
fi

echo "3. Node dependencies and React build"
FRONTEND_DIR="${PROJECT_DIR}/frontend"
if [ "${SKIP_BUILD}" = "1" ] && [ -d "${FRONTEND_DIR}/dist" ]; then
  echo "Skipping npm build (SKIP_BUILD=1, dist/ exists)"
else
  echo "Installing Node dependencies (npm ci)"
  (cd "$FRONTEND_DIR" && npm ci --silent)
  echo "Building React frontend"
  (cd "$FRONTEND_DIR" && npm run build)
  echo "Frontend built at ${FRONTEND_DIR}/dist/"
fi

echo "4. Start FastAPI on port ${SERVER_PORT}"
LOGS_DIR="${PROJECT_DIR}/logs"
mkdir -p "${LOGS_DIR}"
API_LOG="${LOGS_DIR}/fastapi.log"
API_PID="${LOGS_DIR}/fastapi.pid"

if [ "${EFFECTIVE_OLLAMA_URL}" = "${LOCAL_OLLAMA_URL}" ] && [ -x "${PROJECT_DIR}/scripts/start_ollama_local.sh" ]; then
  echo "Ensuring sibling local Ollama is running at ${LOCAL_OLLAMA_URL}"
  OLLAMA_HOST="${LOCAL_OLLAMA_URL}" "${PROJECT_DIR}/scripts/start_ollama_local.sh"
fi

_goat_systemd_restart() {
  local unit="$1"
  if systemctl --user is-enabled "$unit" >/dev/null 2>&1; then
    echo "Restarting FastAPI via systemd (${unit})"
    systemctl --user restart "$unit"
    sleep 2
    echo "MainPID: $(systemctl --user show "$unit" --property=MainPID --value 2>/dev/null || echo '?')"
    return 0
  fi
  return 1
}

SYSTEMD_USED=0
SELECTED_PORT="${SERVER_PORT}"
stop_pidfile "$API_PID"
if _goat_systemd_restart goat-ai; then
  SYSTEMD_USED=1
  echo "Waiting for FastAPI on ${SELECTED_PORT} via systemd"
  if ! healthcheck_port "${SELECTED_PORT}"; then
    echo "systemd target ${SELECTED_PORT} did not become healthy; falling back to nohup."
    systemctl --user stop goat-ai 2>/dev/null || true
    SYSTEMD_USED=0
    SELECTED_PORT=""
  fi
fi

if [ "${SYSTEMD_USED}" != "1" ]; then
  echo "Freeing port ${SERVER_PORT}"
  free_port "${SERVER_PORT}"
  echo "Starting FastAPI on 0.0.0.0:${SERVER_PORT} (log: ${API_LOG})"
  GOAT_SERVER_PORT="${SERVER_PORT}" GOAT_LOCAL_PORT="${SERVER_PORT}" nohup "${VENV_DIR}/bin/python" -m uvicorn server:create_app \
    --factory \
    --host 0.0.0.0 \
    --port "${SERVER_PORT}" \
    --workers 2 \
    >> "$API_LOG" 2>&1 &
  echo $! > "$API_PID"
  echo "PID: $(cat "$API_PID")"

  echo "Waiting for FastAPI on ${SERVER_PORT}"
  if healthcheck_port "${SERVER_PORT}"; then
    SELECTED_PORT="${SERVER_PORT}"
    echo "FastAPI health OK on ${SERVER_PORT}"
  else
    stop_pidfile "$API_PID"
    echo "FastAPI did not become healthy on ${SERVER_PORT}. Check ${API_LOG}"
    exit 1
  fi
fi

if [ -z "${SELECTED_PORT}" ]; then
  echo "FastAPI did not become healthy on ${SERVER_PORT}. Check ${API_LOG}"
  exit 1
fi

echo "5. Post-deploy checks"
echo "Running post-deploy contract checks..."
if ! "${VENV_DIR}/bin/python" "${PROJECT_DIR}/scripts/post_deploy_check.py" --base-url "http://127.0.0.1:${SELECTED_PORT}"; then
  echo "Post-deploy contract checks failed."
  exit 1
fi

echo ""
echo "Deployment complete"
echo "React UI:   https://ai.simonbb.com/mingzhi/"
echo "API health: http://127.0.0.1:${SELECTED_PORT}/api/health"
echo ""
echo "FastAPI log: tail -f ${API_LOG}"
echo "Stop:        kill \$(cat ${API_PID})"
echo ""
