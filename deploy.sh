#!/usr/bin/env bash
# GOAT AI — one-shot server deploy (Streamlit + optional Vite frontend build)
# Usage: chmod +x deploy.sh && ./deploy.sh
# Override branch, e.g.: GIT_BRANCH=python_version ./deploy.sh

set -euo pipefail

# --- Configuration Section ---
REPO_URL="${REPO_URL:-https://github.com/mingzhi0119/GOAT_AI.git}"
PROJECT_DIR="${PROJECT_DIR:-$HOME/GOAT_AI}"
# Default main; use python_version (or your deploy branch) when needed
GIT_BRANCH="${GIT_BRANCH:-python_version}"
PORT="${PORT:-62606}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-$PROJECT_DIR/.venv}"
APP_FILE="${APP_FILE:-app.py}"
# Optional: export OLLAMA_BASE_URL before running if Ollama is not on localhost:11434
#
# If manual `git pull` fails (e.g. local package-lock.json edits), sync to remote with:
#   git fetch origin && git reset --hard "origin/${GIT_BRANCH:-python_version}"

echo "🛠️ Starting Deployment Sequence for GOAT AI..."

free_port() {
  local p="$1"
  if command -v fuser >/dev/null 2>&1; then
    fuser -k "${p}/tcp" 2>/dev/null || true
  fi
  if command -v lsof >/dev/null 2>&1; then
    if lsof -ti ":${p}" >/dev/null 2>&1; then
      lsof -ti ":${p}" | xargs -r kill -9 2>/dev/null || true
    fi
  fi
}

# 1. Environment Synchronization
if [ ! -d "$PROJECT_DIR/.git" ]; then
  echo "📂 Directory not found. Executing initial git clone..."
  git clone "$REPO_URL" "$PROJECT_DIR"
fi

echo "🔄 Synchronizing repository (branch: $GIT_BRANCH)..."
cd "$PROJECT_DIR"
git fetch --all --prune
git checkout "$GIT_BRANCH"
git reset --hard "origin/${GIT_BRANCH}"

# 2. Python virtualenv and dependencies
if [ ! -x "$VENV_DIR/bin/python" ]; then
  echo "🐍 Creating virtualenv at $VENV_DIR..."
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

echo "📦 Installing Python dependencies..."
"$VENV_DIR/bin/pip" install --upgrade pip
if [ -f requirements.txt ]; then
  "$VENV_DIR/bin/pip" install -r requirements.txt
else
  echo "⚠️  requirements.txt not found; skipping pip install."
fi

# 3. Optional frontend (Vite/React under frontend/)
if [ -f frontend/package.json ]; then
  echo "📦 Installing frontend dependencies (npm)..."
  (cd frontend && (npm ci || npm install))
  if grep -q '"build"' frontend/package.json 2>/dev/null; then
    echo "🏗️  Compiling frontend assets..."
    (cd frontend && npm run build)
  fi
fi

# 4. Process cleanup on deployment port
echo "🧹 Freeing port $PORT..."
free_port "$PORT"

# 5. Launch Streamlit (project root: app.py)
LOG_FILE="${PROJECT_DIR}/streamlit.log"
STREAMLIT_BIN="$VENV_DIR/bin/streamlit"
if [ ! -x "$STREAMLIT_BIN" ]; then
  echo "❌ streamlit not found in venv. Ensure requirements.txt includes streamlit."
  exit 1
fi

echo "🚀 Starting Streamlit on 0.0.0.0:$PORT (log: $LOG_FILE)..."
nohup "$STREAMLIT_BIN" run "$APP_FILE" \
  --server.port "$PORT" \
  --server.address 0.0.0.0 \
  --server.headless true \
  >> "$LOG_FILE" 2>&1 &
echo $! > "${PROJECT_DIR}/streamlit.pid"

# 6. Deployment verification
sleep 3
HEALTH_URL="http://127.0.0.1:${PORT}/_stcore/health"
BASE_URL="http://127.0.0.1:${PORT}/"
LISTEN_OK=false
if command -v ss >/dev/null 2>&1 && ss -tln 2>/dev/null | grep -q ":${PORT}"; then
  LISTEN_OK=true
elif command -v netstat >/dev/null 2>&1 && netstat -tln 2>/dev/null | grep -q ":${PORT}"; then
  LISTEN_OK=true
fi

PID_OK=false
if [ -f "${PROJECT_DIR}/streamlit.pid" ]; then
  SPID="$(cat "${PROJECT_DIR}/streamlit.pid" 2>/dev/null || true)"
  if [ -n "$SPID" ] && kill -0 "$SPID" 2>/dev/null; then
    PID_OK=true
  fi
fi

if curl -sf "$HEALTH_URL" >/dev/null 2>&1; then
  echo "✅ GOAT AI is responding (Streamlit health check OK)."
elif curl -sf "$BASE_URL" >/dev/null 2>&1; then
  echo "✅ App answered on port $PORT (HTTP OK)."
elif [ "$LISTEN_OK" = true ] || [ "$PID_OK" = true ]; then
  echo "✅ Streamlit appears to be up (port or PID check). If the browser fails, check $LOG_FILE and the reverse proxy."
else
  echo "❌ Deployment may have failed. Check $LOG_FILE (and that python/venv paths are correct)."
  exit 1
fi

echo "🔗 Local URL: http://127.0.0.1:${PORT}/"
echo "   (Public URL depends on your reverse proxy, e.g. https://ai.simonbb.com/mingzhi/)"
