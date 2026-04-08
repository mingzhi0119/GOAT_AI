# GOAT AI Operations

## Runtime targets

- Local development backend: `:62606`
- Frontend dev server: `:3000`
- Production server target: `:62606`
- Runtime target API: `GET /api/system/runtime-target`

Runtime target resolution now follows a single-port policy: always `GOAT_SERVER_PORT` (default `62606`), with no `8002` fallback.

## Development

Backend:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
lint-imports
python3 -m uvicorn server:app --host 0.0.0.0 --port 62606 --reload
```

`lint-imports` enforces backend package layering (`pyproject.toml`); run it after dependency or router/service refactors.

### SQLite schema migrations (Phase 13 §13.0)

On startup, `log_service.init_db` runs **`backend/services/db_migrations.apply_migrations`**, which executes `backend/migrations/NNN_*.sql` in order and records each file’s SHA-256 in the `schema_migrations` table. If a migration file changes after apply, the process **refuses to start** (checksum mismatch). Add new DDL only as a new numbered SQL file.

API error responses use a stable envelope (`detail`, `code`, optional `request_id`); see [API_ERRORS.md](API_ERRORS.md).

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
- Deploy now includes a post-deploy contract check (`scripts/post_deploy_check.py`) before success is reported

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
| `OLLAMA_CHAT_FIRST_EVENT_TIMEOUT` | `/api/chat` first SSE event timeout seconds | `90` |
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
| `GOAT_LOCAL_PORT` | Deprecated alias (single-port policy uses `GOAT_SERVER_PORT`) | `62606` |
| `GOAT_GPU_UUID` | Preferred GPU UUID | empty |
| `GOAT_GPU_INDEX` | GPU index fallback | `0` |
| `GOAT_LATENCY_ROLLING_MAX_SAMPLES` | Inference average sample window | `20` |
| `GOAT_MODEL_CAP_CACHE_TTL_SEC` | Model capability cache TTL seconds (`0` disables cache) | `60` |
| `GOAT_LOG_JSON` | Emit JSON log lines (stderr) with `request_id` and structured `extra` fields | `false` |
| `GOAT_READY_SKIP_OLLAMA_PROBE` | Omit Ollama `GET /api/tags` from `/api/ready` (SQLite-only) | `false` |
| `GOAT_OLLAMA_READ_RETRY_ATTEMPTS` | Max attempts for idempotent Ollama reads (`/api/tags`, `/api/show`) | `3` |
| `GOAT_OLLAMA_READ_RETRY_BASE_MS` | Exponential backoff base delay (ms) for idempotent Ollama reads | `120` |
| `GOAT_OLLAMA_READ_RETRY_JITTER_MS` | Added random jitter (ms) for idempotent Ollama read retries | `80` |
| `GOAT_OLLAMA_CIRCUIT_BREAKER_FAILURES` | Consecutive failed read operations before opening breaker | `3` |
| `GOAT_OLLAMA_CIRCUIT_BREAKER_OPEN_SEC` | Seconds the read breaker remains open before half-open probe | `20` |
| `GOAT_IDEMPOTENCY_TTL_SEC` | Idempotency record TTL (seconds) for upload analyze + chat session append | `300` |
| `GOAT_MAX_CHAT_MESSAGES` | Max message count accepted by `POST /api/chat` (422 if exceeded) | `120` |
| `GOAT_MAX_CHAT_PAYLOAD_BYTES` | Max UTF-8 request payload bytes accepted by `POST /api/chat` (422 if exceeded) | `512000` |

### Structured logging (Phase 13 Wave A)

- Inbound `X-Request-ID` is honored; otherwise the server assigns one. It is bound for the request in a context var and appears on log lines and JSON error bodies.
- With `GOAT_LOG_JSON=1`, root logs are JSON objects. Access-style lines from `goat_ai.access` include `route`, `status`, and `duration_ms`. Error responses from exception handlers include the same `X-Request-ID` as log correlation.
- Example line (pretty-printed; production is one line per event):

```json
{"ts": "2026-04-07 12:00:00,000", "level": "INFO", "logger": "goat_ai.access", "message": "http_request", "request_id": "550e8400-e29b-41d4-a716-446655440000", "route": "/api/history", "status": 200, "duration_ms": 2.145}
```

### Metrics (Prometheus)

- `GET /api/system/metrics` returns Prometheus text (same auth as other protected APIs when `GOAT_API_KEY` is set).
- Scrape with the API key header, for example: `curl -sS -H "X-GOAT-API-Key: $GOAT_API_KEY" http://127.0.0.1:62606/api/system/metrics`
- Histogram contract: `http_request_duration_seconds` is exposed as standard Prometheus histogram series:
  - `http_request_duration_seconds_bucket{le="..."}`
  - `http_request_duration_seconds_sum`
  - `http_request_duration_seconds_count`
- Counter semantics: `chat_stream_completed_total` counts only successful assistant completions (token path followed by `done`), not safeguard-blocked refusal flows.

### Ollama client resilience policy (Phase 13 Wave B)

- Scope: only idempotent metadata reads (`GET /api/tags`, `POST /api/show`).
- Retries: exponential backoff + jitter using `GOAT_OLLAMA_READ_RETRY_*`.
- Circuit breaker: `closed -> open -> half_open` using `GOAT_OLLAMA_CIRCUIT_BREAKER_*`.
- Timeouts remain unchanged (`timeout=5` for tags/show probes). Streamed chat uses `OLLAMA_CHAT_FIRST_EVENT_TIMEOUT` for the first response chunk, while non-stream generation keeps `OLLAMA_GENERATE_TIMEOUT`.
- Retryability registry source remains `backend/api_errors.py` (documented stable codes); this policy does not change API error envelope semantics.

### Idempotency keys (Phase 13 Wave B)

- `POST /api/upload/analyze`: accepts optional `Idempotency-Key`.
- `POST /api/chat`: accepts optional `Idempotency-Key` when `session_id` is present (session append path).
- Same key + same payload returns the same response body.
- Same key + different payload returns `409` (`code = IDEMPOTENCY_CONFLICT`).
- Storage: SQLite `idempotency_keys` table (TTL cleanup on claim), suited to single-process deployment.

### Multi-instance stance (honest limits)

- Rate limiting in `backend/http_security.py` is in-memory and per-process.
- Rolling latency samples (`/api/system/inference`) are process-local.
- Idempotency cache is SQLite-backed in this release; concurrent multi-writer behavior across many app instances is not treated as a cluster-wide guarantee.
- Mitigations without Redis/Postgres:
  - Use sticky sessions at the proxy layer.
  - Lower per-instance rate limits to preserve global headroom.
  - Aggregate metrics externally (Prometheus scrape per instance, then sum/quantile at query level).
  - Keep one writable app process for SQLite when possible.

### Performance and capacity (Phase 13.3)

SLO starter table:

| SLO item | Target | Source |
|----------|--------|--------|
| First-token latency p95 | <= 2000 ms | `GET /api/system/inference` (`first_token_p95_ms`) |
| Full chat latency p95 | <= 12000 ms | `GET /api/system/inference` (`chat_p95_ms`) |
| Max concurrent SSE streams (single process) | 20 | Runbook load validation (`tools/load_chat_smoke.py`) |
| Upload analyze JSON budget | <= 5 s for <= 20 MB CSV/XLSX | `POST /api/upload/analyze` smoke run |
| Session append guardrails | hard-stop at configured maxes | `GOAT_MAX_CHAT_MESSAGES`, `GOAT_MAX_CHAT_PAYLOAD_BYTES` |

Load smoke command:

```bash
python tools/load_chat_smoke.py --base-url http://127.0.0.1:62606 --model gemma4:26b --runs 20 --show-system-inference
```

When API protection is enabled, pass `--api-key "$GOAT_API_KEY"`.

## Process and health

- Liveness: `GET /api/health`
- Readiness: `GET /api/ready` (SQLite + optional Ollama probe; use `GOAT_READY_SKIP_OLLAMA_PROBE=1` when Ollama is intentionally absent)
- Logs: `logs/fastapi.log`
- PID file in nohup mode: `logs/fastapi.pid`

Stop commands:

```bash
kill "$(cat logs/fastapi.pid)"
```

```powershell
Stop-Process -Id (Get-Content .\logs\fastapi.pid)
```

## Backup and restore

- Runbook: [BACKUP_RESTORE.md](BACKUP_RESTORE.md)
- One-command backup:

```bash
python scripts/backup_chat_db.py
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
| GET | `/api/ready` |
| GET | `/api/system/metrics` |
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
