# GOAT AI — Server Environment & FastAPI + React Migration Plan

> Recorded: 2026-03-30  
> Server: `A100` — Simon Business School, University of Rochester  
> User: `jupyter-mhu29@simon.roches-bde1e` (TLJH / JupyterHub managed account)

---

## 1. Current Server Environment

### 1.1 OS & Hardware

| Item | Value |
|------|-------|
| OS | Ubuntu 24.04.4 LTS (Noble) |
| Kernel | 6.8.0-101-generic x86_64 |
| CPU Cores | 32 |
| RAM | 125 GB total · **115 GB available** |
| Disk | 3.6 TB total · **920 GB free** on `/` |
| GPU | NVIDIA A100 (machine hostname) |

### 1.2 Runtime Versions

| Runtime | Version | Notes |
|---------|---------|-------|
| Python | **3.12.6** | Managed by TLJH conda at `/opt/tljh/` |
| pip | 26.0.1 | User-writable via `pip install --user` |
| conda | 24.7.1 | Available at `/opt/tljh/user/bin/conda` |
| Node.js | **v18.19.1** | Pre-installed; **cannot be upgraded** (TLJH system) |
| npm | 9.2.0 | Paired with Node 18 |
| npx | 9.2.0 | Available |

### 1.3 Already-Installed Python Packages (relevant)

| Package | Version | Location |
|---------|---------|----------|
| uvicorn | 0.35.0 | `/opt/tljh/user/lib/python3.12` (system) |
| pydantic / pydantic-core | latest | system |
| starlette | available | system |
| anyio, sniffio, idna | latest | system |
| streamlit | current | system |
| pandas | 2.2.3 | system |
| requests | 2.32.3 | system |

`fastapi` itself is **not yet installed** but dry-run confirms it installs cleanly  
(only 4 extra packages: `annotated-doc`, `fastapi`, `starlette`, `typing-inspection`).

### 1.4 Network & Ports

| Port | Status | Process |
|------|--------|---------|
| **8000** | LISTEN (10.222.60.10 only) | Unknown internal service |
| **8001** | LISTEN (0.0.0.0) | `uvicorn` — already externally reachable |
| **8501** | LISTEN (0.0.0.0) | `streamlit` — current GOAT AI |
| **8002** | **FREE** ✅ | Target port for new FastAPI server |

- Internal IP: `10.222.60.10`
- Public IP: `128.151.203.65`
- nginx: installed but **inactive** (disabled) — can be activated later with admin help
- `ufw`: no sudo access → cannot modify firewall rules
- High ports (`> 1024`) on `0.0.0.0` are externally reachable (confirmed by 8001/8501)

### 1.5 Permissions & Constraints

| Constraint | Detail |
|-----------|--------|
| No `sudo` | Cannot start system services, modify firewall, or install to `/usr/` |
| pip install | Works with `--user` flag; some system packages already in TLJH env |
| Node.js upgrade | **Blocked** — managed by TLJH, cannot change system Node version |
| Port binding | Only ports > 1024, bound to `0.0.0.0` are accessible externally |

---

## 2. Version Constraints (Node 18.19.1)

Node 18.19.1 is the **LTS "Hydrogen"** release. All current tooling is compatible.

| Tool | Max Supported | Recommended Pin | Notes |
|------|--------------|-----------------|-------|
| **React** | 19.x | `react@18.3` | React 19 works; 18.3 is battle-tested LTS |
| **Vite** | 6.x | `vite@5.4` | Vite 6 works; v5 has wider plugin compat |
| **React Router** | 7.x | `react-router-dom@6` | v7 works but v6 is stable |
| **TypeScript** | 5.x | `typescript@5.3` | Full support |
| **Tailwind CSS** | 3.x | `tailwindcss@3.4` | v4 requires Node 20+ |
| **Next.js** | 15.x | — | Overkill for this use-case; not recommended |
| **axios / fetch** | any | native `fetch` | Node 18 has native fetch |

> **Avoid**: Tailwind v4, Turbopack (needs Node 20+), React Native.

---

## 3. Target Architecture

```
Browser
  │
  ▼
FastAPI  (port 8002, uvicorn)
  ├── GET  /                   → serves React build (dist/index.html)
  ├── GET  /assets/*           → serves React static assets
  ├── GET  /api/models         → Ollama model list
  ├── POST /api/chat           → Ollama streaming (SSE)
  └── POST /api/upload         → CSV/XLSX analysis
         │
         ▼
    Ollama (localhost:11434)
```

**Single process, single port** — no nginx needed. React is compiled to static files
and served directly by FastAPI's `StaticFiles` mount.

### Folder Structure (target)

```
GOAT_AI/
├── backend/                  # FastAPI application
│   ├── main.py               # App factory, static files mount
│   ├── routers/
│   │   ├── chat.py           # SSE streaming endpoint
│   │   ├── models.py         # Ollama model list
│   │   └── upload.py         # CSV/XLSX analysis
│   └── requirements.txt      # backend-only deps
├── frontend/                 # React + Vite
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   └── FileUpload.tsx
│   │   └── hooks/
│   │       └── useChat.ts    # SSE streaming hook
│   ├── public/
│   └── package.json          # React 18, Vite 5
├── goat_ai/                  # Shared Python logic (KEEP, reuse)
│   ├── ollama_client.py      ✅ reuse as-is
│   ├── tools.py              ✅ reuse as-is
│   ├── config.py             ✅ reuse as-is
│   ├── uploads.py            ✅ reuse as-is
│   └── types.py              ✅ reuse as-is
├── app.py                    # Keep (Streamlit fallback during transition)
├── server.py                 # New FastAPI entrypoint
└── deploy.sh                 # Updated to start uvicorn on 8002
```

---

## 4. Migration Plan

### Phase 0 — Environment Verification (1–2 hours)

**Goal**: Confirm the stack works end-to-end before writing any feature code.

- [ ] `pip install fastapi` and confirm import works
- [ ] Write a 5-line FastAPI hello-world, start on port 8002, confirm it's reachable at `http://128.151.203.65:8002/`
- [ ] Run `npm create vite@5 frontend -- --template react-ts` in `~/GOAT_AI/`
- [ ] `cd frontend && npm install && npm run build` — confirm build succeeds with Node 18
- [ ] Mount `frontend/dist` as `StaticFiles` in FastAPI and confirm React page loads on port 8002
- [ ] **Go / No-Go decision** before Phase 1

---

### Phase 1 — FastAPI Backend (1–2 days)

**Goal**: Full feature-parity backend replacing Streamlit's Python logic.

| Task | File | Reuses |
|------|------|--------|
| App factory + CORS + static files | `backend/main.py` | — |
| Model list endpoint `GET /api/models` | `backend/routers/models.py` | `goat_ai/ollama_client.py` |
| Streaming chat `POST /api/chat` (SSE) | `backend/routers/chat.py` | `goat_ai/ollama_client.py` |
| File upload + analysis `POST /api/upload` | `backend/routers/upload.py` | `goat_ai/uploads.py`, `goat_ai/tools.py` |
| Config / env loading | `backend/config.py` | `goat_ai/config.py` |
| Update `requirements.txt` | root | add `fastapi`, `python-multipart` |

**Key decisions**:
- SSE (Server-Sent Events) for streaming — simpler than WebSocket, native browser `EventSource`
- Session state via simple in-memory dict keyed by `session_id` cookie (no Redis needed)
- All existing `goat_ai/*.py` modules imported directly — zero rewrite

---

### Phase 2 — React Frontend (2–3 days)

**Goal**: Modern chat UI with full feature parity + native theme switching.

| Component | Description |
|-----------|-------------|
| `App.tsx` | Root layout, theme provider, router |
| `Sidebar.tsx` | Logo, model selector, Refresh, Clear chat, file upload, "Powered by Mingzhi Hu" |
| `ChatWindow.tsx` | Message list, auto-scroll |
| `MessageBubble.tsx` | User / assistant bubbles, markdown rendering |
| `FileUpload.tsx` | Drag-and-drop CSV/XLSX |
| `useChat.ts` | Hook: manages SSE stream, message list, pending state |
| `useTheme.ts` | Hook: Light/Dark toggle via `localStorage` + CSS class on `<html>` |
| `theme.css` | CSS variables for Simon branding colors in both modes |

**Tech stack**:
```json
"react": "^18.3",
"vite": "^5.4",
"typescript": "^5.3",
"react-markdown": "^9",
"tailwindcss": "^3.4"
```

**Features gained over Streamlit**:
- True Light/Dark toggle (CSS variables, instant — no page reload)
- Smooth streaming animation (token-by-token rendering)
- No full-page re-render on any interaction
- Proper scroll-to-bottom behavior
- Responsive layout

---

### Phase 3 — Integration & Deployment (half day)

**Goal**: Single-command start, Streamlit kept as fallback.

- [ ] Update `deploy.sh`: add `uvicorn server:app --host 0.0.0.0 --port 8002 --workers 2`
- [ ] Add `server.py` as FastAPI entrypoint that mounts `frontend/dist`
- [ ] Add `npm run build` step to deploy script (or commit `dist/` to repo)
- [ ] Test end-to-end: upload CSV → analyze → streaming response → theme toggle
- [ ] Keep `streamlit run app.py` on port 8501 as fallback until professor sign-off

---

### Phase 4 — Polish & Handoff (1 day)

- [ ] Add loading skeleton while waiting for first SSE token
- [ ] Error boundary in React (show friendly message if backend is down)
- [ ] Copy-to-clipboard button on assistant messages
- [ ] Update `OPERATIONS.md` with new start/stop commands
- [ ] Demo to professor, get approval to retire Streamlit

---

## 5. Risk Register

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| Port 8002 blocked externally | Low (8001 confirms ports are open) | Try 8003, 8004 |
| TLJH process manager kills long-running uvicorn | Medium | Use `nohup` + PID file (same as current deploy.sh) |
| Node 18 incompatibility with a package | Low | All pinned versions verified against Node 18 |
| Professor prefers Streamlit for grading | Medium | Keep Streamlit on 8501 in parallel until Phase 4 sign-off |
| SSE blocked by intermediate proxy | Low | Fall back to polling `/api/chat/stream?token` pattern |

---

## 6. Quick Reference — Key Commands

```bash
# Install backend
pip install fastapi python-multipart

# Scaffold frontend
npm create vite@5 frontend -- --template react-ts
cd frontend && npm install

# Dev mode (two terminals)
uvicorn server:app --reload --port 8002          # terminal 1
cd frontend && npm run dev -- --port 3000        # terminal 2

# Production build + serve
cd frontend && npm run build                     # outputs to frontend/dist/
uvicorn server:app --host 0.0.0.0 --port 8002 --workers 2

# Access
http://128.151.203.65:8002/     # new React UI
http://128.151.203.65:8501/     # existing Streamlit (fallback)
```
