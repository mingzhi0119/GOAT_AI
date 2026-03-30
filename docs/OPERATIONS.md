# GOAT AI — Install, run, deploy, stop

> **Current architecture (Phase 2):** FastAPI backend on `:8002` + React/Vite frontend.
> The React bundle is compiled and served as static files by FastAPI in production.

---

## Quick start (development)

### 1. Python backend

```bash
cd "$HOME/GOAT_AI"   # or your clone path
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # then edit as needed
python3 -m uvicorn server:app --host 0.0.0.0 --port 8002 --reload
```

### 2. React frontend (dev mode, hot-reload on :3000)

```bash
cd frontend
npm ci
npm run dev
```

Open `http://localhost:3000/`. Vite proxies `/api/*` → `http://localhost:8002`.

---

## Production build

```bash
# Build the React SPA (outputs to frontend/dist/)
cd frontend && npm ci && npm run build && cd ..

# Start FastAPI (serves both API and SPA)
python3 -m uvicorn server:app --host 0.0.0.0 --port 8002
```

FastAPI auto-detects `frontend/dist/` and mounts it as a static file server (see `backend/main.py`).

---

## Deploy (A100 server)

```bash
bash deploy.sh
```

- **Logs:** `fastapi.log` in the project root.
- **PID:** `fastapi.pid`
- **Stop:** `kill "$(cat fastapi.pid)"`

---

## Environment variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `GOAT_OLLAMA_BASE_URL` | Ollama HTTP base URL | `http://127.0.0.1:11434` |
| `GOAT_GENERATE_TIMEOUT` | Request timeout in seconds | `120` |
| `GOAT_MAX_UPLOAD_MB` | Max file upload size (MB) | `25` |
| `GOAT_MAX_DATAFRAME_ROWS` | Max rows loaded from CSV/XLSX | `50000` |
| `GOAT_SYSTEM_PROMPT` | Optional system prompt override | _(built-in default)_ |
| `GOAT_SYSTEM_PROMPT_FILE` | Path to UTF-8 file with system prompt | _(none)_ |
| `GOAT_CORS_ORIGINS` | Comma-separated CORS allow-origins | `http://localhost:3000` |

---

## Access URLs

| URL | Description |
|-----|-------------|
| `https://ai.simonbb.com/mingzhi/` | **Public URL** — nginx proxies to FastAPI on :62606 |
| `http://127.0.0.1:62606/api/health` | Internal health check |

## Health check

```bash
curl -sf http://127.0.0.1:62606/api/health
# → {"status":"ok","version":"1.0.0"}
```

---

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Liveness probe |
| `GET` | `/api/models` | List Ollama model names |
| `POST` | `/api/chat` | SSE streaming chat completion |
| `POST` | `/api/upload` | SSE streaming CSV/XLSX analysis |

**SSE format** (chat & upload):
```
data: "token"\n\n   ← each token is a JSON-encoded string
data: "[DONE]"\n\n  ← stream terminator
data: "[ERROR] …"\n\n followed by "[DONE]" on Ollama errors
```

---

## Frontend stack (Phase 2)

| Tool | Version | Purpose |
|------|---------|---------|
| Vite | 5 | Build tool + dev server |
| React | 18 | UI framework |
| TypeScript | 5 (strict) | Type safety |
| Tailwind CSS | 3.4 | Utility-first styling |
| react-markdown | 9 | Markdown rendering in chat |
| remark-gfm | 4 | GFM tables, strikethrough, task lists |

---

## Data handling

Uploaded CSV/XLSX is read into memory for the request only; nothing is persisted to disk.

---

## Reverse proxy (school host)

Nginx or Apache: proxy `https://…/` → `http://127.0.0.1:8002/`. Standard proxy headers required:

```nginx
proxy_set_header Connection '';
proxy_http_version 1.1;
proxy_buffering off;      # required for SSE
proxy_cache off;
proxy_set_header X-Accel-Buffering no;
```
