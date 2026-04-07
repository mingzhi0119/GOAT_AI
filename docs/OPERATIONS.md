# GOAT AI Operations

## Runtime targets

- Local development backend: `:8002`
- Frontend dev server: `:3000`
- Production server target: `:62606`
- Runtime target API: `GET /api/system/runtime-target`

`GOAT_DEPLOY_TARGET=auto` prefers `GOAT_SERVER_PORT` and falls back to `GOAT_LOCAL_PORT` only when needed.

## Development

Backend:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 -m uvicorn server:app --host 0.0.0.0 --port 8002 --reload
```

Frontend:

```bash
cd frontend
npm ci
npm run dev
```

## Deploy

Linux:

```bash
bash deploy.sh
QUICK=1 bash deploy.sh
SKIP_BUILD=1 bash deploy.sh
SYNC_GIT=1 bash deploy.sh
```

Windows PowerShell:

```powershell
.\deploy.ps1
.\deploy.ps1 -Quick
.\deploy.ps1 -SkipBuild
.\deploy.ps1 -SyncGit
```

Important behavior:

- Deploy defaults to the current checkout
- `SYNC_GIT=1` is explicit opt-in
- `deploy.sh` keeps the `nohup` + `logs/fastapi.pid` fallback path
- Windows deploy reuses Ollama on `127.0.0.1:11434` when available unless `OLLAMA_BASE_URL` is explicitly set

## Shared-host constraints

This project is designed for an unprivileged JupyterHub-style server environment:

- No `sudo` / no root
- Do not assume nginx reload access
- `systemctl --user` may work, but may also be unavailable in SSH sessions
- `nohup` fallback must remain supported
- Preferred GPU target is the A100:
  - `GOAT_GPU_UUID=GPU-fb2cf8f7-e9bf-f136-a3bb-e150426598e8`

## Key environment variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `OLLAMA_BASE_URL` | Ollama HTTP base URL | `http://127.0.0.1:11434` |
| `OLLAMA_GENERATE_TIMEOUT` | LLM request timeout seconds | `120` |
| `GOAT_MAX_UPLOAD_MB` | Max upload size | `20` |
| `GOAT_MAX_DATAFRAME_ROWS` | Max parsed rows | `50000` |
| `GOAT_SYSTEM_PROMPT` | Override system prompt | built-in default |
| `GOAT_SYSTEM_PROMPT_FILE` | Path to UTF-8 prompt file | empty |
| `GOAT_LOG_PATH` | SQLite path | `<project>/chat_logs.db` |
| `GOAT_API_KEY` | Protect non-health APIs via `X-GOAT-API-Key` | empty |
| `GOAT_RATE_LIMIT_WINDOW_SEC` | Rate limit window | `60` |
| `GOAT_RATE_LIMIT_MAX_REQUESTS` | Max requests per window | `60` |
| `GOAT_DEPLOY_TARGET` | `auto`, `server`, or `local` | `auto` |
| `GOAT_SERVER_PORT` | Preferred server port | `62606` |
| `GOAT_LOCAL_PORT` | Local fallback port | `8002` |
| `GOAT_GPU_UUID` | Preferred GPU UUID | empty |
| `GOAT_GPU_INDEX` | GPU index fallback | `0` |
| `GOAT_LATENCY_ROLLING_MAX_SAMPLES` | Inference average sample window | `20` |

## Process and health

- Health endpoint: `GET /api/health`
- Logs: `logs/fastapi.log`
- PID file in nohup mode: `logs/fastapi.pid`

Stop commands:

```bash
kill "$(cat logs/fastapi.pid)"
```

```powershell
Stop-Process -Id (Get-Content .\logs\fastapi.pid)
```

## GPU and telemetry

Telemetry endpoints:

- `GET /api/system/gpu`
- `GET /api/system/inference`

If `nvidia-smi` is unavailable or unreadable, GPU telemetry should degrade gracefully instead of showing fake values.

## API ops summary

| Method | Path |
|--------|------|
| GET | `/api/health` |
| GET | `/api/models` |
| GET | `/api/models/capabilities` |
| POST | `/api/chat` |
| POST | `/api/upload` |
| POST | `/api/upload/analyze` |
| GET | `/api/history` |
| GET | `/api/history/{session_id}` |
| DELETE | `/api/history` |
| DELETE | `/api/history/{session_id}` |
| GET | `/api/system/gpu` |
| GET | `/api/system/inference` |
| GET | `/api/system/runtime-target` |

For exact request and response details, use [API_REFERENCE.md](API_REFERENCE.md).
