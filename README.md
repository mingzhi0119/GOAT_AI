# GOAT AI

**Strategic Intelligence assistant for Simon Business School, University of Rochester.**

- Public URL: <https://ai.simonbb.com/mingzhi/>
- Repo: <https://github.com/mingzhi0119/GOAT_AI> · branch `main`
- **Current snapshot (features, APIs, deploy pitfalls):** [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md)
- **API contract:** [docs/API_REFERENCE.md](docs/API_REFERENCE.md)
- Version line in this README may lag; trust **PROJECT_STATUS** + **ROADMAP** for “what shipped”.

---

## Tech Stack

| Layer | Technology | Version | Role |
|-------|-----------|---------|------|
| **Server** | Ubuntu 24.04, NVIDIA A100 | — | Production host |
| **Python runtime** | CPython | 3.12.6 | Backend language |
| **Backend framework** | FastAPI + Uvicorn | 0.135 / 0.35 | REST + SSE API |
| **LLM runtime** | Ollama | latest | Local model serving |
| **Frontend build** | Vite | 8 | Build tool + dev server |
| **Frontend UI** | React + TypeScript | 19 / 5 | SPA |
| **Styling** | Tailwind CSS | 3.4 | Utility-first CSS |
| **Markdown** | react-markdown + remark-gfm | 9 / 4 | Chat message rendering |
| **Data** | pandas + openpyxl | 2.2 / 3.1 | CSV/XLSX analysis |
| **Chat logging** | SQLite (stdlib) | — | Q&A persistence |
| **Reverse proxy** | Nginx | school-managed | TLS + path routing |
| **Node** | Node.js | 24.14.1 | Frontend build (CI/prod, managed via `nvm`) |

---

## Architecture

```
Browser
  │  HTTPS
  ▼
Nginx  (ai.simonbb.com/mingzhi/)
  │  proxy_pass http://127.0.0.1:62606
  ▼
FastAPI / Uvicorn  :62606  ──► React SPA (frontend/dist/ served as static files)
  │
  ├── GET  /api/health          liveness probe
  ├── GET  /api/models          list Ollama models
  ├── POST /api/chat            SSE streaming chat  ──► Ollama /api/chat
  └── POST /api/upload          SSE streaming file analysis
                                          │
                                          └──► chat_logs.db  (SQLite, every Q&A)
```

**Request flow (chat):**

1. React sends `POST /api/chat` with `{model, messages[]}`.
2. `backend/routers/chat.py` validates the request and calls `stream_chat_sse()`.
3. `backend/services/chat_service.py` streams tokens from Ollama via SSE, buffers the full response.
4. On completion, `backend/services/log_service.py` writes one row to `chat_logs.db`.
5. React assembles tokens into a message bubble in real time.

---

## Directory Structure

```
GOAT_AI/
│
├── server.py                   Uvicorn entrypoint (re-exports backend.main:app)
├── deploy.sh                   Deploy: git pull, pip, npm build, FastAPI on :62606
├── goat-ai.service             Example user systemd unit (port 62606)
├── requirements.txt            Python dependencies (pinned)
├── __tests__/                  Python unit tests (`unittest`; `python -m unittest discover -s __tests__`)
│
├── backend/                    FastAPI application
│   ├── main.py                 App factory: CORS, routers, SPA mount, DB init
│   ├── config.py               Server-only config (port, CORS origins)
│   ├── dependencies.py         FastAPI dependency providers (LLMClient)
│   ├── models/
│   │   └── chat.py             Pydantic request/response schemas
│   ├── routers/
│   │   ├── chat.py             POST /api/chat
│   │   ├── models.py           GET  /api/models
│   │   └── upload.py           POST /api/upload
│   └── services/
│       ├── chat_service.py     stream_chat_sse() — token streaming + logging
│       ├── upload_service.py   CSV/XLSX → Ollama analysis
│       └── log_service.py      SQLite init + log_conversation()
│
├── goat_ai/                    Shared library (used by FastAPI)
│   ├── config.py               Settings dataclass, load_settings(), env vars
│   ├── ollama_client.py        LLMClient — wraps Ollama HTTP API
│   ├── types.py                ChatTurn TypedDict
│   ├── exceptions.py           OllamaUnavailable
│   ├── logging_config.py       Structured logging setup
│   └── …                       (tools, uploads)
│
├── frontend/                   React + Vite SPA
│   ├── src/
│   │   ├── App.tsx             Root layout: Sidebar + ChatWindow
│   │   ├── components/
│   │   │   ├── Sidebar.tsx     Left panel: logo, model selector, actions, upload
│   │   │   ├── ChatWindow.tsx  Chat area: messages + input box + welcome screen
│   │   │   ├── MessageBubble.tsx  Markdown message renderer
│   │   │   ├── FileUpload.tsx  Drag-and-drop CSV/XLSX upload
│   │   │   ├── GoatIcon.tsx    PNG logo with gold rounded border
│   │   │   └── ErrorBoundary.tsx  React error boundary
│   │   ├── hooks/
│   │   │   ├── useChat.ts      Chat state + SSE streaming
│   │   │   ├── useModels.ts    Ollama model list fetch
│   │   │   └── useTheme.ts     Light/dark toggle + localStorage
│   │   ├── api/                Typed fetch wrappers (chat, models, upload)
│   │   └── styles/global.css   CSS variables (brand colours, dark mode)
│   ├── public/
│   │   ├── golden_goat_icon.png  App icon
│   │   └── simon_logo.svg      Simon Business School wordmark
│   ├── dist/                   Built SPA — served by FastAPI in production
│   ├── vite.config.ts
│   ├── tailwind.config.cjs
│   └── package.json
│
├── tools/
│   └── query_logs.py           CLI to inspect chat_logs.db (no sqlite3 needed)
│
├── static/
│   ├── golden_goat_icon.png
│   └── urochester_simon_business_horizontal.svg
│
├── docs/
│   ├── OPERATIONS.md           Install, deploy, env vars, API reference, chat logs
│   ├── ROADMAP.md              Shipped phases + upcoming features + decision log
│   └── ENGINEERING_STANDARDS.md  Coding conventions
│
└── .env.example                All supported env vars with defaults
```

---

## Quick Start

### Development

```bash
# 1. Clone & Python setup
git clone https://github.com/mingzhi0119/GOAT_AI.git
cd GOAT_AI
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # edit OLLAMA_BASE_URL if needed

# 2. Start backend (hot-reload)
python3 -m uvicorn server:app --host 0.0.0.0 --port 8002 --reload

# 3. Start frontend dev server (separate terminal)
cd frontend && npm ci && npm run dev
# → open http://localhost:3000
```

### Production (A100 server)

```bash
# Full deploy (first time, or after requirements.txt changed)
bash deploy.sh

# Quick update (code + frontend only, no pip)
QUICK=1 bash deploy.sh
```

See [`docs/OPERATIONS.md`](docs/OPERATIONS.md) for all options. With systemd, install `goat-ai.service`; otherwise `deploy.sh` uses `nohup` and `fastapi.pid`.

---

## Chat Log Queries (no sqlite3 required)

```bash
python3 tools/query_logs.py recent          # last 20 Q&A pairs
python3 tools/query_logs.py recent 50       # last 50
python3 tools/query_logs.py stats           # daily usage counts
python3 tools/query_logs.py search Porter   # keyword search
python3 tools/query_logs.py export > logs.csv
```

---

## Key Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama API endpoint |
| `GOAT_LOG_PATH` | `<project>/chat_logs.db` | SQLite chat log location |
| `GOAT_MAX_UPLOAD_MB` | `20` | Max file upload size |
| `GOAT_CORS_ORIGINS` | `http://localhost:3000` | Allowed CORS origins |

Full list: [`.env.example`](.env.example) · [`docs/OPERATIONS.md`](docs/OPERATIONS.md)

---

## Backend tests

From the repo root (with the venv activated and dev dependencies as needed):

```bash
python -m unittest discover -s __tests__ -p "test_*.py" -v
```

---

## Further Reading

| Doc | Content |
|-----|---------|
| [`docs/OPERATIONS.md`](docs/OPERATIONS.md) | Deploy, stop, env vars, API reference, chat log schema |
| [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md) | Endpoint-by-endpoint request/response/error contract |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Shipped phases, upcoming features, infrastructure decisions |
| [`docs/ENGINEERING_STANDARDS.md`](docs/ENGINEERING_STANDARDS.md) | Coding conventions and quality rules |
