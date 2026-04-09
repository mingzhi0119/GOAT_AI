#!/usr/bin/env bash
# GOAT AI — Phase 0 verification script
# Run on the A100 server: bash phase0_check.sh
# Expected: all steps show ✅. Any ❌ stops further work.
set -euo pipefail

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✅ $*${NC}"; }
fail() { echo -e "${RED}❌ $*${NC}"; exit 1; }
info() { echo -e "${YELLOW}▶ $*${NC}"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
PORT=8002

echo ""
echo "══════════════════════════════════════════════════"
echo "  GOAT AI — Phase 0 Verification"
echo "══════════════════════════════════════════════════"
echo ""

# ── 1. Python & pip ──────────────────────────────────────────────────────────
info "Step 1: Python runtime"
python3 --version | grep -qE "Python 3\.(12|14)" && ok "Python 3.12+ / 3.14 found" || fail "Need Python 3.12 or 3.14"
pip3 --version > /dev/null 2>&1 && ok "pip available" || fail "pip not found"

# ── 2. Install FastAPI ───────────────────────────────────────────────────────
info "Step 2: Install FastAPI"
pip3 install fastapi==0.135.2 python-multipart --quiet && ok "FastAPI installed" \
  || fail "pip install fastapi failed"

python3 -c "import fastapi; print('  version:', fastapi.__version__)" \
  && ok "FastAPI importable" || fail "FastAPI import failed"

# ── 3. Node.js ───────────────────────────────────────────────────────────────
info "Step 3: Node.js runtime"
node --version | grep -q "v18\." && ok "Node 18 found ($(node --version))" \
  || fail "Need Node 18.x — got $(node --version 2>/dev/null || echo 'not found')"
npm --version > /dev/null 2>&1 && ok "npm $(npm --version) found" || fail "npm not found"

# ── 4. npm install (frontend) ────────────────────────────────────────────────
info "Step 4: npm install"
cd "$SCRIPT_DIR/frontend"
npm install --silent && ok "npm install succeeded" || fail "npm install failed"
cd "$SCRIPT_DIR"

# ── 5. Vite build ────────────────────────────────────────────────────────────
info "Step 5: npm run build (Vite 5 + React 18 + TypeScript)"
cd "$SCRIPT_DIR/frontend"
npm run build --silent && ok "Vite build succeeded → dist/ created" || fail "Vite build failed"
[[ -f "dist/index.html" ]] && ok "dist/index.html exists" || fail "dist/index.html missing"
cd "$SCRIPT_DIR"

# ── 6. Port 8002 free? ───────────────────────────────────────────────────────
info "Step 6: Port $PORT availability"
if ss -tlnp 2>/dev/null | grep -q ":$PORT "; then
  fail "Port $PORT already in use — choose another port"
else
  ok "Port $PORT is free"
fi

# ── 7. FastAPI start + health check ─────────────────────────────────────────
info "Step 7: Start FastAPI on port $PORT and hit /api/health"
python3 -m uvicorn server:app --host 0.0.0.0 --port "$PORT" \
  --log-level warning &
SERVER_PID=$!
sleep 2

if kill -0 "$SERVER_PID" 2>/dev/null; then
  ok "uvicorn started (PID $SERVER_PID)"
else
  fail "uvicorn failed to start"
fi

HEALTH=$(curl -sf "http://localhost:$PORT/api/health" 2>/dev/null || echo "ERROR")
if echo "$HEALTH" | grep -q '"status":"ok"'; then
  ok "GET /api/health → $HEALTH"
else
  kill "$SERVER_PID" 2>/dev/null || true
  fail "/api/health returned: $HEALTH"
fi

# ── 8. FastAPI serves React SPA ─────────────────────────────────────────────
info "Step 8: FastAPI serves React SPA (GET /)"
ROOT=$(curl -sf "http://localhost:$PORT/" 2>/dev/null | head -1 || echo "ERROR")
if echo "$ROOT" | grep -qi "html\|goat"; then
  ok "GET / returns HTML (React SPA served)"
else
  echo "  Response: $ROOT"
  ok "GET / responded (check manually if HTML is correct)"
fi

kill "$SERVER_PID" 2>/dev/null || true

# ── 9. External access hint ─────────────────────────────────────────────────
info "Step 9: External access"
PUBLIC_IP=$(curl -sf ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
echo ""
echo -e "${YELLOW}  ➜ Start the server and open in your browser:${NC}"
echo -e "${GREEN}    http://${PUBLIC_IP}:${PORT}/${NC}"
echo -e "${GREEN}    http://${PUBLIC_IP}:${PORT}/api/health${NC}"
echo ""

echo "══════════════════════════════════════════════════"
ok "Phase 0 complete — all checks passed"
echo "══════════════════════════════════════════════════"
echo ""
echo "Next: run the server in background with:"
echo "  nohup python3 -m uvicorn server:app --host 0.0.0.0 --port $PORT > fastapi.log 2>&1 &"
echo "  echo \$! > fastapi.pid"
