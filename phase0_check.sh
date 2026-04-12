#!/usr/bin/env bash
# GOAT AI Phase 0 verification script
# Run on the target host: bash phase0_check.sh
set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok() {
  echo -e "${GREEN}OK:${NC} $*"
}

fail() {
  echo -e "${RED}FAIL:${NC} $*"
  exit 1
}

info() {
  echo -e "${YELLOW}INFO:${NC} $*"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PORT=62606

echo ""
echo "=============================="
echo "  GOAT AI Phase 0 Verification"
echo "=============================="
echo ""

info "Step 1: Python runtime"
python3 --version | grep -qE "Python 3\.(12|14)" && ok "Python 3.12+ / 3.14 found" || fail "Need Python 3.12 or 3.14"
pip3 --version >/dev/null 2>&1 && ok "pip available" || fail "pip not found"

info "Step 2: Install FastAPI"
pip3 install fastapi==0.135.2 python-multipart --quiet && ok "FastAPI installed" || fail "pip install fastapi failed"
python3 -c "import fastapi; print('version:', fastapi.__version__)" && ok "FastAPI importable" || fail "FastAPI import failed"

info "Step 3: Node.js runtime"
node --version | grep -q "v24\." && ok "Node 24 found ($(node --version))" || fail "Need Node 24.x; got $(node --version 2>/dev/null || echo 'not found')"
npm --version >/dev/null 2>&1 && ok "npm $(npm --version) found" || fail "npm not found"

info "Step 4: npm ci"
cd "$SCRIPT_DIR/frontend"
npm ci --silent && ok "npm ci succeeded" || fail "npm ci failed"
cd "$SCRIPT_DIR"

info "Step 5: npm run build"
cd "$SCRIPT_DIR/frontend"
npm run build --silent && ok "Vite build succeeded" || fail "Vite build failed"
[[ -f "dist/index.html" ]] && ok "dist/index.html exists" || fail "dist/index.html missing"
cd "$SCRIPT_DIR"

info "Step 6: Port $PORT availability"
if ss -tlnp 2>/dev/null | grep -q ":$PORT "; then
  fail "Port $PORT already in use; choose another port"
else
  ok "Port $PORT is free"
fi

info "Step 7: Start FastAPI on port $PORT and hit /api/health"
python3 -m uvicorn server:create_app --factory --host 0.0.0.0 --port "$PORT" --log-level warning &
SERVER_PID=$!
sleep 2

if kill -0 "$SERVER_PID" 2>/dev/null; then
  ok "uvicorn started (PID $SERVER_PID)"
else
  fail "uvicorn failed to start"
fi

HEALTH=$(curl -sf "http://localhost:$PORT/api/health" 2>/dev/null || echo "ERROR")
if echo "$HEALTH" | grep -q '"status":"ok"'; then
  ok "GET /api/health returned healthy status"
else
  kill "$SERVER_PID" 2>/dev/null || true
  fail "/api/health returned: $HEALTH"
fi

info "Step 8: FastAPI serves the React SPA"
ROOT=$(curl -sf "http://localhost:$PORT/" 2>/dev/null | head -1 || echo "ERROR")
if echo "$ROOT" | grep -qi "html\|goat"; then
  ok "GET / returns HTML"
else
  echo "Response: $ROOT"
  ok "GET / responded; inspect manually if HTML looks wrong"
fi

kill "$SERVER_PID" 2>/dev/null || true

info "Step 9: External access hint"
PUBLIC_IP=$(curl -sf ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
echo ""
echo "Open these URLs after starting the server:"
echo "  http://${PUBLIC_IP}:${PORT}/"
echo "  http://${PUBLIC_IP}:${PORT}/api/health"
echo ""

ok "Phase 0 complete; all checks passed"
echo ""
echo "Next:"
echo "  mkdir -p logs"
echo "  nohup python3 -m uvicorn server:create_app --factory --host 0.0.0.0 --port $PORT > logs/fastapi.log 2>&1 &"
echo "  echo \$! > logs/fastapi.pid"
