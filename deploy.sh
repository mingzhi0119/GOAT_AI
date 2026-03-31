#!/usr/bin/env bash
# GOAT AI — production deploy (FastAPI + React on :62606, Streamlit fallback on :8501)
# Usage:
#   bash deploy.sh              # full deploy (git pull → pip → build → restart)
#   QUICK=1 bash deploy.sh      # quick restart: git pull → npm build → restart API only
#   SKIP_BUILD=1 bash deploy.sh # skip npm build (use existing dist/)
#   SKIP_STREAMLIT=1 bash deploy.sh # skip Streamlit fallback
#
# Override any variable before running, e.g.:
#   PORT_API=8003 bash deploy.sh

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

PORT_API="${PORT_API:-62606}"          # FastAPI + React SPA (proxied via ai.simonbb.com/mingzhi/)
PORT_STREAMLIT="${PORT_STREAMLIT:-8501}"  # Streamlit fallback (kept for reference)

SKIP_BUILD="${SKIP_BUILD:-0}"
SKIP_STREAMLIT="${SKIP_STREAMLIT:-0}"
QUICK="${QUICK:-0}"

# QUICK=1 implies skip pip + skip Streamlit
if [ "${QUICK}" = "1" ]; then
  SKIP_STREAMLIT=1
fi

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

# ── 1. Git sync ───────────────────────────────────────────────────────────────
if [ ! -d "${PROJECT_DIR}/.git" ]; then
  echo "📂 Cloning repository…"
  git clone "$REPO_URL" "$PROJECT_DIR"
fi

echo "🔄 Syncing to origin/${GIT_BRANCH}…"
cd "$PROJECT_DIR"
git fetch --all --prune
git checkout "$GIT_BRANCH"
git reset --hard "origin/${GIT_BRANCH}"
echo "✅ Repository up to date."

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
NODE_MODULES="${FRONTEND_DIR}/node_modules"

if [ ! -d "$NODE_MODULES" ]; then
  echo "📦 Installing Node dependencies (npm ci)…"
  (cd "$FRONTEND_DIR" && npm ci --silent)
fi

if [ "${SKIP_BUILD}" = "1" ] && [ -d "${FRONTEND_DIR}/dist" ]; then
  echo "⚡ Skipping npm build (SKIP_BUILD=1, dist/ exists)."
else
  echo "⚙️  Building React frontend…"
  (cd "$FRONTEND_DIR" && npm run build)
  echo "✅ Frontend built → ${FRONTEND_DIR}/dist/"
fi

# ── 4. Start FastAPI (uvicorn) on PORT_API ────────────────────────────────────
API_LOG="${PROJECT_DIR}/fastapi.log"
API_PID="${PROJECT_DIR}/fastapi.pid"

if systemctl --user is-enabled goat-ai >/dev/null 2>&1; then
  # ── systemd path (preferred after one-time setup) ────────────────────────
  echo "🚀 Restarting FastAPI via systemd (goat-ai.service)…"
  systemctl --user restart goat-ai
  sleep 2
  echo "   MainPID: $(systemctl --user show goat-ai --property=MainPID --value 2>/dev/null || echo '?')"
else
  # ── nohup fallback (works without systemd setup) ─────────────────────────
  echo "🧹 Freeing port ${PORT_API}…"
  free_port "$PORT_API"

  if [ -f "$API_PID" ]; then
    OLD_PID="$(cat "$API_PID" 2>/dev/null || true)"
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
      kill "$OLD_PID" 2>/dev/null || true
      sleep 1
    fi
    rm -f "$API_PID"
  fi

  echo "🚀 Starting FastAPI on 0.0.0.0:${PORT_API} (log: ${API_LOG})…"
  nohup "${VENV_DIR}/bin/python" -m uvicorn server:app \
    --host 0.0.0.0 \
    --port "$PORT_API" \
    --workers 2 \
    >> "$API_LOG" 2>&1 &
  echo $! > "$API_PID"
  echo "   PID: $(cat "$API_PID")"
fi

# ── 5. Health check — FastAPI ─────────────────────────────────────────────────
echo "⏳ Waiting for FastAPI to come up…"
for i in {1..15}; do
  if curl -sf "http://127.0.0.1:${PORT_API}/api/health" >/dev/null 2>&1; then
    echo "✅ FastAPI health check passed."
    break
  fi
  sleep 1
  if [ "$i" -eq 15 ]; then
    echo "❌ FastAPI did not respond within 15 s. Check ${API_LOG}"
    exit 1
  fi
done

# ── 6. Streamlit fallback on PORT_STREAMLIT (optional) ────────────────────────
if [ "${SKIP_STREAMLIT}" != "1" ]; then
  STREAMLIT_BIN="${VENV_DIR}/bin/streamlit"
  if [ -x "$STREAMLIT_BIN" ]; then
    SL_LOG="${PROJECT_DIR}/streamlit.log"
    SL_PID="${PROJECT_DIR}/streamlit.pid"

    echo "🧹 Freeing port ${PORT_STREAMLIT}…"
    free_port "$PORT_STREAMLIT"

    if [ -f "$SL_PID" ]; then
      OLD_PID="$(cat "$SL_PID" 2>/dev/null || true)"
      if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        kill "$OLD_PID" 2>/dev/null || true
        sleep 1
      fi
      rm -f "$SL_PID"
    fi

    echo "🚀 Starting Streamlit fallback on 0.0.0.0:${PORT_STREAMLIT} (log: ${SL_LOG})…"
    nohup "$STREAMLIT_BIN" run app.py \
      --server.port "$PORT_STREAMLIT" \
      --server.address 0.0.0.0 \
      --server.headless true \
      >> "$SL_LOG" 2>&1 &
    echo $! > "$SL_PID"
    echo "   Streamlit PID: $(cat "$SL_PID")"
  else
    echo "⚠️  streamlit not found in venv; skipping fallback."
  fi
else
  echo "⏭️  Skipping Streamlit (SKIP_STREAMLIT=1)."
fi

# ── 7. Summary ────────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════"
echo "  GOAT AI — Deployment Complete"
echo "════════════════════════════════════════════"
echo ""
  echo "  🌐 React UI  → https://ai.simonbb.com/mingzhi/"
  echo "  🔌 API health→ http://127.0.0.1:${PORT_API}/api/health"
if [ "${SKIP_STREAMLIT}" != "1" ]; then
  echo "  📊 Streamlit → http://128.151.203.65:${PORT_STREAMLIT}/ (fallback)"
fi
echo ""
echo "  📄 FastAPI log:    tail -f ${API_LOG}"
echo "  🛑 Stop FastAPI:   kill \$(cat ${API_PID})"
if [ "${SKIP_STREAMLIT}" != "1" ]; then
  echo "  📄 Streamlit log:  tail -f ${PROJECT_DIR}/streamlit.log"
  echo "  🛑 Stop Streamlit: kill \$(cat ${PROJECT_DIR}/streamlit.pid)"
fi
echo ""
