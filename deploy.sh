#!/usr/bin/env bash
# GOAT AI — production deploy (FastAPI + React on :62606)
# Usage:
#   bash deploy.sh                   # full deploy from current local working tree
#   QUICK=1 bash deploy.sh           # quick restart: skip pip install
#   SKIP_BUILD=1 bash deploy.sh      # skip npm build (use existing dist/)
#   SYNC_GIT=1 bash deploy.sh        # optional: reset to origin/$GIT_BRANCH before deploy
#
# Override any variable before running, e.g.:
#   GOAT_SERVER_PORT=62606 bash deploy.sh

_DEPLOY_SCRIPT="${BASH_SOURCE[0]:-$0}"
if [[ -f "$_DEPLOY_SCRIPT" ]]; then
  chmod +x "$_DEPLOY_SCRIPT" 2>/dev/null || true
fi
unset _DEPLOY_SCRIPT

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────
REPO_URL="${REPO_URL:-https://github.com/mingzhi0119/GOAT_AI.git}"
PROJECT_DIR="${PROJECT_DIR:-$HOME/GOAT_AI}"
GIT_BRANCH="${GIT_BRANCH:-main}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-$PROJECT_DIR/.venv}"

LOCAL_OLLAMA_URL="${LOCAL_OLLAMA_URL:-http://127.0.0.1:11435}"
SERVER_PORT="${GOAT_SERVER_PORT:-62606}"
EFFECTIVE_OLLAMA_URL="${OLLAMA_BASE_URL:-${LOCAL_OLLAMA_URL}}"

SKIP_BUILD="${SKIP_BUILD:-0}"
QUICK="${QUICK:-0}"
SYNC_GIT="${SYNC_GIT:-0}"

echo "🛠️  GOAT AI — Deploy starting (branch: ${GIT_BRANCH})${QUICK:+ [QUICK mode]}"

# ── Helper: free a TCP port ───────────────────────────────────────────────────
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
  for i in {1..15}; do
    if curl -sf "http://127.0.0.1:${p}/api/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

# ── Helper: stop process from pidfile if alive ────────────────────────────────
stop_pidfile() {
  local pidfile="$1"
  if [ -f "$pidfile" ]; then
    local old_pid
    old_pid="$(cat "$pidfile" 2>/dev/null || true)"
    if [ -n "$old_pid" ] && kill -0 "$old_pid" 2>/dev/null; then
      kill "$old_pid" 2>/dev/null || true
      sleep 1
    fi
    rm -f "$pidfile"
  fi
}

# ── 1. Project checkout ───────────────────────────────────────────────────────
if [ ! -d "${PROJECT_DIR}/.git" ]; then
  echo "📂 Cloning repository…"
  git clone "$REPO_URL" "$PROJECT_DIR"
fi

cd "$PROJECT_DIR"
git checkout "$GIT_BRANCH"

if [ "${SYNC_GIT}" = "1" ]; then
  echo "🔄 Syncing to origin/${GIT_BRANCH}…"
  git fetch --all --prune
  git reset --hard "origin/${GIT_BRANCH}"
  echo "✅ Repository synced to origin/${GIT_BRANCH}."
else
  echo "📍 Deploying current local checkout on ${GIT_BRANCH} (SYNC_GIT=0)."
fi

# ── 2. Python virtualenv + deps (skipped in QUICK mode) ──────────────────────
if [ "${QUICK}" = "1" ]; then
  echo "⚡ [QUICK] Skipping Python venv / pip install."
  if [ ! -x "${VENV_DIR}/bin/python" ]; then
    echo "❌ Venv not found at ${VENV_DIR}. Run a full deploy first."
    exit 1
  fi
else
  if [ ! -x "${VENV_DIR}/bin/python" ]; then
    echo "🐍 Creating virtualenv at ${VENV_DIR}…"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
  fi

  echo "📦 Installing Python dependencies…"
  "${VENV_DIR}/bin/pip" install --upgrade pip --quiet
  "${VENV_DIR}/bin/pip" install -r requirements.txt --quiet
  echo "✅ Python deps installed."
fi

# ── 3. Node / npm deps + React build ─────────────────────────────────────────
FRONTEND_DIR="${PROJECT_DIR}/frontend"

if [ "${SKIP_BUILD}" = "1" ] && [ -d "${FRONTEND_DIR}/dist" ]; then
  echo "⚡ Skipping npm build (SKIP_BUILD=1, dist/ exists)."
else
  echo "📦 Installing Node dependencies (npm ci)…"
  (cd "$FRONTEND_DIR" && npm ci --silent)
  echo "⚙️  Building React frontend…"
  (cd "$FRONTEND_DIR" && npm run build)
  echo "✅ Frontend built → ${FRONTEND_DIR}/dist/"
fi

# ── 4. Start FastAPI (uvicorn) on PORT_API ────────────────────────────────────
LOGS_DIR="${PROJECT_DIR}/logs"
mkdir -p "${LOGS_DIR}"
API_LOG="${LOGS_DIR}/fastapi.log"
API_PID="${LOGS_DIR}/fastapi.pid"

if [ "${EFFECTIVE_OLLAMA_URL}" = "${LOCAL_OLLAMA_URL}" ] && [ -x "${PROJECT_DIR}/scripts/start_ollama_local.sh" ]; then
  echo "🦙 Ensuring sibling local Ollama is running at ${LOCAL_OLLAMA_URL}…"
  OLLAMA_HOST="${LOCAL_OLLAMA_URL}" "${PROJECT_DIR}/scripts/start_ollama_local.sh"
fi

_goat_systemd_restart() {
  local unit="$1"
  if systemctl --user is-enabled "$unit" >/dev/null 2>&1; then
    echo "🚀 Restarting FastAPI via systemd (${unit})…"
    systemctl --user restart "$unit"
    sleep 2
    echo "   MainPID: $(systemctl --user show "$unit" --property=MainPID --value 2>/dev/null || echo '?')"
    return 0
  fi
  return 1
}

SYSTEMD_USED=0
SELECTED_PORT="${SERVER_PORT}"
echo "🧹 Freeing port ${SERVER_PORT}…"
free_port "${SERVER_PORT}"
stop_pidfile "$API_PID"

if _goat_systemd_restart goat-ai; then
  SYSTEMD_USED=1
  echo "⏳ Waiting for FastAPI on ${SELECTED_PORT} via systemd…"
  if ! healthcheck_port "${SELECTED_PORT}"; then
    echo "⚠️ systemd target ${SELECTED_PORT} did not become healthy; falling back to nohup target resolution."
    systemctl --user stop goat-ai 2>/dev/null || true
    SYSTEMD_USED=0
    SELECTED_PORT=""
  fi
fi

if [ "${SYSTEMD_USED}" != "1" ]; then
  # ── nohup fallback (works without systemd setup) ─────────────────────────
  echo "🚀 Starting FastAPI on 0.0.0.0:${SERVER_PORT} (log: ${API_LOG})…"
  GOAT_PORT="${SERVER_PORT}" nohup "${VENV_DIR}/bin/python" -m uvicorn server:app \
    --host 0.0.0.0 \
    --port "${SERVER_PORT}" \
    --workers 2 \
    >> "$API_LOG" 2>&1 &
  echo $! > "$API_PID"
  echo "   PID: $(cat "$API_PID")"

  echo "⏳ Waiting for FastAPI on ${SERVER_PORT}…"
  if healthcheck_port "${SERVER_PORT}"; then
    SELECTED_PORT="${SERVER_PORT}"
    echo "✅ FastAPI health OK on ${SERVER_PORT}."
  else
    stop_pidfile "$API_PID"
    echo "❌ FastAPI did not become healthy on ${SERVER_PORT}. Check ${API_LOG}"
    exit 1
  fi
fi

# ── 5. Health check — FastAPI ─────────────────────────────────────────────────
if [ -z "${SELECTED_PORT}" ]; then
  echo "❌ FastAPI did not become healthy on ${SERVER_PORT}. Check ${API_LOG}"
  exit 1
fi

echo "🧪 Running post-deploy contract checks..."
if ! "${VENV_DIR}/bin/python" "${PROJECT_DIR}/scripts/post_deploy_check.py" --base-url "http://127.0.0.1:${SELECTED_PORT}"; then
  echo "❌ Post-deploy contract checks failed."
  exit 1
fi

# ── 6. Summary ────────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════"
echo "  GOAT AI — Deployment Complete"
echo "════════════════════════════════════════════"
echo ""
echo "  🌐 React UI  → https://ai.simonbb.com/mingzhi/"
echo "  🔌 API health→ http://127.0.0.1:${SELECTED_PORT}/api/health"
echo ""
echo "  📄 FastAPI log:  tail -f ${API_LOG}"
echo "  🛑 Stop:         kill \$(cat ${API_PID})"
echo ""
