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
bash deploy.sh              # full deploy
QUICK=1 bash deploy.sh      # git pull + npm ci + npm build + restart (npm ci ensures new frontend deps)
```

- **Logs:** `fastapi.log` in the project root.
- **PID:** `fastapi.pid` (nohup mode only)
- **Stop (nohup):** `kill "$(cat fastapi.pid)"`
- **Stop (systemd):** `systemctl --user stop goat-ai`

---

## Process supervisor (one-time setup, recommended)

Sets up `systemd --user` so the server restarts automatically after crashes or reboots.
Run these commands once on the A100 server:

```bash
mkdir -p ~/.config/systemd/user
cp ~/GOAT_AI/goat-ai.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable goat-ai
systemctl --user start goat-ai
loginctl enable-linger $USER   # keep service running when not logged in
```

After this, `bash deploy.sh` automatically uses `systemctl --user restart goat-ai` instead of nohup.

Useful commands:

```bash
systemctl --user status goat-ai        # check if running
systemctl --user restart goat-ai       # manual restart
journalctl --user -u goat-ai -f        # live logs (alternative to tail -f fastapi.log)
```

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
| `GOAT_LOG_PATH` | Path to SQLite chat log database | `<project_root>/chat_logs.db` |
| `GOAT_GPU_UUID` | Optional GPU UUID lock for `/api/system/gpu` (overrides index) | _(empty)_ |
| `GOAT_GPU_INDEX` | GPU index for `/api/system/gpu` when UUID not set | `0` |

---

## Access URLs

| URL | Description |
|-----|-------------|
| `https://ai.simonbb.com/mingzhi/` | **Public URL** — nginx proxies to FastAPI on :62606 |
| `http://127.0.0.1:62606/api/health` | Internal health check |

---

## GPU telemetry (A100) for UI status strip

These checks confirm the server can provide **real** GPU stats for a sidebar status indicator.

### One-shot probe (A100 only)

```bash
nvidia-smi --id=0 \
  --query-gpu=name,uuid,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw \
  --format=csv,noheader,nounits
```

Expected: one line for `NVIDIA A100-SXM4-80GB`.

### Real-time probe (1 Hz)

```bash
nvidia-smi --id=0 \
  --query-gpu=timestamp,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw \
  --format=csv,noheader,nounits -l 1
```

Press `Ctrl+C` to stop before entering the next command.

### Permissions sanity check

```bash
which nvidia-smi
ls -l /dev/nvidia0 /dev/nvidiactl
id
groups
```

If these fail, do not show fake GPU values in UI; return a graceful "Telemetry unavailable".

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
| `GET` | `/api/system/gpu` | GPU telemetry JSON for sidebar status strip |

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

## Chat logs

Every completed chat request is appended to a local SQLite database (`chat_logs.db` in the project root by default).

### Schema

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Auto-increment primary key |
| `created_at` | TEXT | ISO-8601 UTC timestamp |
| `ip` | TEXT | Client IP address |
| `model` | TEXT | Ollama model name used |
| `turn_count` | INTEGER | Number of messages in the request history |
| `user_message` | TEXT | The last user message |
| `assistant_response` | TEXT | Full assembled assistant response |
| `response_ms` | INTEGER | Elapsed time from first token to `[DONE]` |

### Querying (SSH to server)

```bash
# Most recent 20 conversations
sqlite3 ~/GOAT_AI/chat_logs.db \
  "SELECT created_at, ip, model, user_message FROM conversations ORDER BY id DESC LIMIT 20;"

# Daily usage counts
sqlite3 ~/GOAT_AI/chat_logs.db \
  "SELECT date(created_at) AS day, COUNT(*) AS cnt FROM conversations GROUP BY day ORDER BY day DESC;"

# Export everything to CSV
sqlite3 -csv -header ~/GOAT_AI/chat_logs.db \
  "SELECT * FROM conversations;" > ~/goat_logs_export.csv

# Search by keyword
sqlite3 ~/GOAT_AI/chat_logs.db \
  "SELECT created_at, user_message FROM conversations WHERE user_message LIKE '%Porter%';"
```

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
