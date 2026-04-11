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
python3.14 -m venv .venv   # use Python 3.14 when available (matches CI; see `.github/workflows/ci.yml`)
source .venv/bin/activate
pip install -r requirements-ci.txt
cp .env.example .env
lint-imports
python3 -m uvicorn server:app --host 0.0.0.0 --port 62606 --reload
```

`lint-imports` enforces backend package layering (`pyproject.toml`); run it after dependency or router/service refactors.

**Repository tools:** run CLI modules from the **repository root** with `python -m tools.<module>` (for example `python -m tools.run_rag_eval`, `python -m tools.check_api_contract_sync`). This avoids setting `PYTHONPATH` manually; `.env` is for app runtime, not your shell. For **`python -m tools.check_api_contract_sync`**, use the **same Python minor as CI (3.14)** so `docs/openapi.json` matches `app.openapi()`. On Windows, **pandas** may not yet ship wheels for 3.14; use WSL to refresh artifacts: `bash scripts/wsl_api_contract_refresh.sh` (requires `uv` in WSL; installs a transient 3.14 env via `uv run`).

### SQLite schema migrations (Phase 13 Section 13.0)

On startup, `log_service.init_db` runs **`backend/services/db_migrations.apply_migrations`**, which executes `backend/migrations/NNN_*.sql` in order and records each file's SHA-256 in the `schema_migrations` table. If a migration file changes after apply, the process **refuses to start** on checksum mismatch. Add new DDL only as a new numbered SQL file.

API error responses use a stable envelope (`detail`, `code`, optional `request_id`); see [API_ERRORS.md](API_ERRORS.md).

Frontend:

```bash
cd frontend
npm ci
npm run dev
```

### Windows desktop prerequisites

For the Tauri-based desktop shell and future packaged Windows app flow, use the bootstrap script instead of manually clicking through installers:

```powershell
.\scripts\install_desktop_prereqs.ps1 -Profile Runtime
.\scripts\install_desktop_prereqs.ps1 -Profile Dev
```

Profiles:

- `Runtime`
  - installs `Microsoft Edge WebView2 Runtime`
  - installs `Ollama` by default so the packaged app can use the local inference runtime
- `Dev`
  - installs `Rustlang.Rustup`
  - installs `Visual Studio Build Tools 2022` with the C++ workload
  - installs `Microsoft Edge WebView2 Runtime`
- `All`
  - installs both runtime and development prerequisites

Current package ids used by the bootstrap script:

- `Microsoft.EdgeWebView2Runtime`
- `Ollama.Ollama`
- `Rustlang.Rustup`
- `Microsoft.VisualStudio.2022.BuildTools`

### Desktop backend sidecar packaging

Phase 19B uses a frozen Python sidecar instead of requiring end users to install Python manually.

Build flow:

```bash
pip install -r requirements-desktop-build.txt
python -m tools.build_desktop_sidecar
cd frontend
npm run desktop:build
```

Important notes:

- `python -m tools.build_desktop_sidecar` builds a per-platform executable with **PyInstaller**
- the output is copied to `frontend/src-tauri/binaries/goat-backend-$TARGET_TRIPLE[.exe]`
- `npm run desktop:build` triggers the same sidecar build automatically through Tauri's `beforeBuildCommand`
- PyInstaller is **not** a cross-compiler; build each platform's sidecar on that platform (or an equivalent CI runner / VM)
- packaged desktop builds move app-owned writable state out of the repository and into the platform app-local-data directory

Desktop sidecar writable paths:

- SQLite DB: `<app_local_data_dir>/chat_logs.db`
- persisted app data: `<app_local_data_dir>/data`
- desktop shell stdout/stderr are not yet persisted to a dedicated file sink; use backend SQLite/data plus the installer-run process logs for diagnostics today

Packaged desktop runtime config:

- The packaged desktop app inherits runtime configuration from the parent OS environment rather than a repo-local `.env`.
- Common runtime knobs for packaged installs are `OLLAMA_BASE_URL`, `GOAT_FEATURE_CODE_SANDBOX`, `GOAT_CODE_SANDBOX_PROVIDER`, and `GOAT_DESKTOP_BACKEND_PORT`.
- Docker is the default sandbox backend for strong isolation. `localhost` is a trusted-dev fallback only and does not enforce the same network guarantees.

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
- `deploy.sh` and `deploy.ps1` now stop the current FastAPI process gracefully first, then force cleanup only if the drain window expires
- Rollback uses an explicit ref: see [ROLLBACK.md](ROLLBACK.md)
- Windows deploy reuses Ollama on `127.0.0.1:11434` when available unless `OLLAMA_BASE_URL` is explicitly set
- Deploy now includes a post-deploy contract check (`scripts/post_deploy_check.py`) before success is reported: it exercises `GET /api/health`, `GET /api/ready`, `GET /api/system/runtime-target`, and a short `POST /api/chat` stream. The chat step passes when the SSE body includes **at least one** `token` or **`thinking`** frame (so thinking-first models still validate), and fails on HTTP errors, empty SSE, or a first-frame `error`

## Deployment profiles

The app is **portable** across environments (see `README.md` **Environments**). The following sections describe **common** profiles, not exclusive ones.

### Shared unprivileged host (reference profile)

Many production installs match an **unprivileged** server (e.g. JupyterHub-style lab user): no root, no system nginx control, optional user systemd.

- No `sudo` / no root
- Do not assume nginx reload access
- `systemctl --user` may work, but may also be unavailable in SSH sessions
- `nohup` fallback must remain supported for deploy scripts
- On multi-GPU hosts, set a **GPU UUID** so telemetry/UI do not bind to the wrong card (example A100):
  - `GOAT_GPU_UUID=GPU-fb2cf8f7-e9bf-f136-a3bb-e150426598e8`

### Other environments

Self-managed VMs, Docker Compose, Kubernetes, or developer laptops use the same codebase with **env-driven** ports and paths. Features that need **strong isolation** (for example Docker-backed code sandbox execution) must stay tied to explicit operator enablement and runtime probes; the shipped `localhost` provider is a weaker trusted-dev fallback, not a like-for-like isolation substitute.

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
| `GOAT_DATA_DIR` | Root directory for persisted uploads, normalized knowledge text, vector indexes, and vision attachments | `<project>/data` (gitignored by default; do not commit) |
| `GOAT_API_KEY` | Protect non-health APIs via `X-GOAT-API-Key` | empty |
| `GOAT_API_KEY_WRITE` | Optional second key: `GET`/`HEAD`/`OPTIONS` may use read key (`GOAT_API_KEY`); other methods require this write key when set | empty |
| `GOAT_API_CREDENTIALS_JSON` | Optional JSON credential registry; each entry may provide `secret` or `secret_sha256`, and when empty the app derives default read/write credentials from `GOAT_API_KEY` and `GOAT_API_KEY_WRITE` | empty |
| `GOAT_REQUIRE_SESSION_OWNER` | When `true`/`1`, chat and history routes require `X-GOAT-Owner-Id` (session scoping) | `false` |
| `GOAT_RATE_LIMIT_WINDOW_SEC` | Rate limit window | `60` |
| `GOAT_RATE_LIMIT_MAX_REQUESTS` | Max requests per window | `60` |
| `GOAT_DEPLOY_TARGET` | `auto`, `server`, or `local` | `auto` |
| `GOAT_SERVER_PORT` | Preferred server port | `62606` |
| `GOAT_LOCAL_PORT` | Deprecated alias (single-port policy uses `GOAT_SERVER_PORT`) | `62606` |
| `GIT_REF` | Explicit branch/tag/commit checkout target for rollback deploys | `main` |
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
| `GOAT_FEATURE_CODE_SANDBOX` | Operator allows code-sandbox feature (`0`/`1`); `effective_enabled` still requires the selected provider runtime probe | `0` |
| `GOAT_FEATURE_AGENT_WORKBENCH` | Operator exposes the shared workbench feature family; actual sub-capability readiness still depends on runtime support (`plan`, `browse`, and `deep_research` are partially implemented, while `canvas`, project memory, and connectors are not) | `0` |
| `GOAT_CODE_SANDBOX_PROVIDER` | Sandbox runtime backend: `docker` (default) or `localhost` (dev fallback) | `docker` |
| `GOAT_DOCKER_SOCKET` | Override Docker socket/pipe path (empty = defaults: Unix `/var/run/docker.sock`, Windows `\\.\pipe\docker_engine`) | empty |
| `GOAT_CODE_SANDBOX_LOCALHOST_SHELL` | Optional shell executable/path override for `localhost` provider | empty |
| `GOAT_CODE_SANDBOX_DEFAULT_IMAGE` | Docker image used for the Phase 18 sandbox runtime | `python:3.12-slim` |
| `GOAT_CODE_SANDBOX_DEFAULT_TIMEOUT_SEC` | Default sandbox execution timeout | `8` |
| `GOAT_CODE_SANDBOX_MAX_TIMEOUT_SEC` | Maximum sandbox timeout accepted from requests | `15` |
| `GOAT_CODE_SANDBOX_MAX_CODE_BYTES` | Max UTF-8 bytes for inline `code` | `32768` |
| `GOAT_CODE_SANDBOX_MAX_COMMAND_BYTES` | Max UTF-8 bytes for inline `command` | `8192` |
| `GOAT_CODE_SANDBOX_MAX_STDIN_BYTES` | Max UTF-8 bytes for inline `stdin` | `16384` |
| `GOAT_CODE_SANDBOX_MAX_INLINE_FILES` | Max seeded inline text files per execution | `8` |
| `GOAT_CODE_SANDBOX_MAX_INLINE_FILE_BYTES` | Max UTF-8 bytes per inline seeded file | `16384` |
| `GOAT_CODE_SANDBOX_MAX_OUTPUT_BYTES` | Max captured stdout/stderr bytes per stream before truncation | `65536` |
| `GOAT_CODE_SANDBOX_CPU_LIMIT` | Docker CPU quota for each sandbox container | `0.5` |
| `GOAT_CODE_SANDBOX_MEMORY_MB` | Docker memory limit (MB) for each sandbox container | `256` |

### Code sandbox operations (Phase 18)

- `POST /api/code-sandbox/exec` now performs real provider-backed execution when:
  - `GOAT_FEATURE_CODE_SANDBOX=1`
  - the selected provider probe succeeds
  - the caller credential includes `sandbox:execute`
- Phase 18A remains intentionally conservative:
  - `sync` is the default; `async` uses in-process dispatch plus queued-execution recovery on startup
  - short-lived execution only
  - one shell-capable preset
  - Docker enforces `network_policy=disabled` by default; `localhost` reports a degraded contract and does not enforce the same network boundary
  - `docker`: no privileged mode and no host Docker socket mounted into the sandbox container
  - `localhost`: intended for trusted local development only; it does not provide Docker-grade isolation
- The execution contract persists durable rows, event timelines, and replayable log chunks in SQLite:
  - `GET /api/code-sandbox/executions/{execution_id}`
  - `GET /api/code-sandbox/executions/{execution_id}/events`
  - `GET /api/code-sandbox/executions/{execution_id}/logs`
- `GET /api/code-sandbox/executions/{execution_id}/logs` is an SSE stream for stdout/stderr replay plus status updates; clients may reconnect with `after_seq=<last_seen_log_sequence>`
- Files written under `outputs/` are surfaced as metadata in the API response, but they are not yet promoted into the artifact workspace model.

### OpenTelemetry (optional, Phase 15.6)

- Default **`GOAT_OTEL_ENABLED=0`** - tracing is off; the app does not eagerly import the OpenTelemetry SDK.
- Set **`GOAT_OTEL_ENABLED=1`** to enable a `TracerProvider`, W3C **`traceparent`** / **`tracestate`** extraction on incoming HTTP requests (`backend/otel_middleware.py`), and spans around Ollama HTTP calls in `goat_ai/ollama_client.py`.
- **`GOAT_OTEL_EXPORTER`:** `console` (default) prints spans to stderr; `otlp` sends to **`OTEL_EXPORTER_OTLP_ENDPOINT`** (OTLP/HTTP traces URL, e.g. `http://127.0.0.1:4318/v1/traces`).
- Standard OpenTelemetry env vars apply alongside the above (see OpenTelemetry Python docs for OTLP tuning).

### Structured logging (Phase 13 Wave A)

- Inbound `X-Request-ID` is honored; otherwise the server assigns one. It is bound for the request in a context var and appears on log lines and JSON error bodies.
- With `GOAT_LOG_JSON=1`, root logs are JSON objects. Access-style lines from `goat_ai.access` include `route`, `status`, and `duration_ms`.
- Error responses from exception handlers include the same `X-Request-ID` used for log correlation.

Example line:

```json
{"ts": "2026-04-07 12:00:00,000", "level": "INFO", "logger": "goat_ai.access", "message": "http_request", "request_id": "550e8400-e29b-41d4-a716-446655440000", "route": "/api/history", "status": 200, "duration_ms": 2.145}

### Credential-backed authorization (Phase 16C)

- The server still accepts `X-GOAT-API-Key` at ingress, but requests now resolve to a request-scoped authorization context with:
  - `principal_id`
  - `tenant_id`
  - `scopes`
  - `credential_id`
  - legacy `X-GOAT-Owner-Id`
- This is credential-backed authorization, not end-user identity.
- When `GOAT_API_CREDENTIALS_JSON` is empty:
  - `GOAT_API_KEY` becomes `principal:read-default` with read scopes
  - `GOAT_API_KEY_WRITE` becomes `principal:write-default` with read+write scopes plus `sandbox:execute`
  - default tenant is `tenant:default`
- Credential registry entries may provide either:
  - `secret` for compatibility with existing deployments
  - `secret_sha256` for non-reversible config storage
- Raw API keys are hashed to SHA-256 in memory before comparison, and credential matching uses constant-time digest comparison.
- Cross-owner or cross-tenant reads are concealed as `404` where possible.
- Missing API key remains `401`; insufficient scope remains `403`.

Example `GOAT_API_CREDENTIALS_JSON`:

```json
[
  {
    "credential_id": "cred-read-analytics",
    "secret_sha256": "replace-with-lowercase-sha256-hex",
    "principal_id": "principal:analytics-read",
    "tenant_id": "tenant:default",
    "status": "active",
    "scopes": ["history:read", "knowledge:read", "media:read", "artifact:read"]
  }
]
```

### Authorization audit events (Phase 16C)

- Logger: `goat_ai.authz`
- Event name: `authorization_decision`
- Stable fields:
  - `principal_id`
  - `tenant_id`
  - `credential_id`
  - `action`
  - `resource_type`
  - `resource_id`
  - `result`
  - `reason_code`
  - `request_id`
- Never log raw API keys or credential secrets.
```

### Metrics (Prometheus)

- `GET /api/system/metrics` returns Prometheus text
- Same auth rules apply as other protected APIs when `GOAT_API_KEY` is set
- Scrape example:

```bash
curl -sS -H "X-GOAT-API-Key: $GOAT_API_KEY" http://127.0.0.1:62606/api/system/metrics
```

- Histogram contract: `http_request_duration_seconds` is exposed as standard Prometheus histogram series:
  - `http_request_duration_seconds_bucket{le="..."}`
  - `http_request_duration_seconds_sum`
  - `http_request_duration_seconds_count`
- Counter semantics: `chat_stream_completed_total` counts only successful assistant completions, not safeguard-blocked refusal flows

### Ollama client resilience policy (Phase 13 Wave B)

- Scope: only idempotent metadata reads (`GET /api/tags`, `POST /api/show`)
- Retries: exponential backoff + jitter using `GOAT_OLLAMA_READ_RETRY_*`
- Circuit breaker: `closed -> open -> half_open` using `GOAT_OLLAMA_CIRCUIT_BREAKER_*`
- Timeouts remain unchanged (`timeout=5` for tags/show probes)
- Streamed chat uses `OLLAMA_CHAT_FIRST_EVENT_TIMEOUT` for the first response chunk, while non-stream generation keeps `OLLAMA_GENERATE_TIMEOUT`
- Retryability registry source remains `backend/api_errors.py`; this policy does not change API error envelope semantics

### Idempotency keys (Phase 13 Wave B)

- `POST /api/upload/analyze`: accepts optional `Idempotency-Key`
- `POST /api/chat`: accepts optional `Idempotency-Key` when `session_id` is present
- Same key + same payload returns the same response body
- Same key + different payload returns `409` (`code = IDEMPOTENCY_CONFLICT`)
- Storage: SQLite `idempotency_keys` table with TTL cleanup on claim

### Safeguard configuration

The regex-based content moderation layer can be tuned or disabled entirely via two env vars.

| Variable | Values | Default | Behavior |
|----------|--------|---------|----------|
| `GOAT_SAFEGUARD_ENABLED` | `true` / `false` | `true` | Master kill-switch. `false` disables all moderation. |
| `GOAT_SAFEGUARD_MODE` | `off` / `input_only` / `output_only` / `full` | `full` | Scope of moderation when enabled. |

**Mode semantics:**

| Mode | Input check | Output check |
|------|-------------|--------------|
| `full` (default) | active | active |
| `input_only` | active | skipped |
| `output_only` | skipped | active |
| `off` | skipped | skipped |

Setting `GOAT_SAFEGUARD_ENABLED=false` and `GOAT_SAFEGUARD_MODE=off` are equivalent — both cause the dependency factory to inject `None`, which the chat streaming stack treats as "allow everything".

**Architecture note:** disabling safeguard injects `None` into the dependency chain. The streaming services already handle `safeguard is None` at every call site without extra conditionals, so there is no risk of a null-pointer path being left open.

### RAG retrieval quality (Phase 14.7)

**Regression:** run `python -m tools.run_rag_eval` (from the repository root) before merge when changing `backend/services/retrieval_quality/`, `tools/run_rag_eval.py`, or `evaldata/`. CI enforces this on every backend job.

**Knobs (environment + request):**

| Control | Where | Behavior |
|---------|--------|----------|
| `GOAT_RAG_RERANK_MODE` | `passthrough` or `lexical` | For `retrieval_profile=default` only, selects vector order vs lexical overlap rerank after the vector stage (`goat_ai/config.py`). |
| `retrieval_profile` | `POST /api/knowledge/search` body | `default` - uses `GOAT_RAG_RERANK_MODE`; `rag3_lexical` / `rag3_quality` - always lexical rerank; `rag3_quality` also enables conservative whitespace query rewrite before search. |
| Vector similarity | Implementation | Scores are backend-specific; there is **no** global numeric score threshold in config-triage uses **hit vs miss** (see metrics) and eval cases. |

**No-hit behavior:** search returns zero citations when nothing ranks above the empty list; `POST /api/knowledge/answers` returns the documented fixed sentence when no hits (after optional attached-document fallback).

**Observability (`GET /api/system/metrics`):**

- `knowledge_retrieval_requests_total{retrieval_profile="...",outcome="hit|miss"}` - one increment per `search_knowledge` execution.
- `knowledge_query_rewrite_applied_total{retrieval_profile="..."}` - increments when conservative rewrite changed the query (`rag3_quality`).

**Golden set:** see [evaldata/README.md](../evaldata/README.md) and `evaldata/VERSION`.

### Multi-instance stance (honest limits)

- Rate limiting in `backend/http_security.py` is in-memory and per-process
- Rolling latency samples (`/api/system/inference`) are process-local
- Idempotency cache is SQLite-backed in this release; concurrent multi-writer behavior across many app instances is not treated as a cluster-wide guarantee
- Mitigations without Redis/Postgres:
  - Use sticky sessions at the proxy layer
  - Lower per-instance rate limits to preserve global headroom
  - Aggregate metrics externally (Prometheus scrape per instance, then sum/quantile at query level)
  - Keep one writable app process for SQLite when possible

### Performance and capacity (Phase 13.3)

SLO starter table:

| SLO item | Target | Source |
|----------|--------|--------|
| First-token latency p95 | <= 2000 ms | `GET /api/system/inference` (`first_token_p95_ms`) |
| Full chat latency p95 | <= 12000 ms | `GET /api/system/inference` (`chat_p95_ms`) |
| Max concurrent SSE streams (single process) | 20 | Runbook load validation (`python -m tools.load_chat_smoke`) |
| Upload analyze JSON budget | <= 5 s for <= 20 MB supported knowledge file (`csv/xlsx/txt/md/pdf/docx`) | `POST /api/upload/analyze` smoke run |
| Session append guardrails | hard-stop at configured maxes | `GOAT_MAX_CHAT_MESSAGES`, `GOAT_MAX_CHAT_PAYLOAD_BYTES` |

Load smoke command:

```bash
python -m tools.load_chat_smoke --base-url http://127.0.0.1:62606 --model gemma4:26b --runs 20 --show-system-inference
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

Graceful shutdown note:

- The deploy scripts send a normal terminate signal first
- They wait up to 30 seconds for the FastAPI worker to exit cleanly
- Forced cleanup is a fallback, not the default path

## Rollback

- Use [ROLLBACK.md](ROLLBACK.md) for the end-to-end ref rollback procedure
- If the rollback is caused by a schema or data regression, pair it with [BACKUP_RESTORE.md](BACKUP_RESTORE.md)

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

## Phase 13 risk triggers

Treat the following as operational stop signs during Phase 13 rollout work:

| Trigger | Response |
|---------|----------|
| Repeated SSE failure or timeout in post-deploy contract checks | Pause Wave B work, inspect `logs/fastapi.log` and Ollama logs, and do not advance the rollout until `/api/chat` emits SSE again. |
| `/api/ready` flapping or sustained non-200 responses | Block Phase 15 structural refactors until readiness and deploy checks are stable across a full deploy cycle. |
| `sqlite_log_write_failures_total` rising over a sustained window | Prioritize backup/restore drill and recovery work before any new persistence feature lands. |

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
| POST | `/api/knowledge/uploads` |
| GET | `/api/knowledge/uploads/{document_id}` |
| POST | `/api/knowledge/ingestions` |
| GET | `/api/knowledge/ingestions/{ingestion_id}` |
| POST | `/api/knowledge/search` |
| POST | `/api/knowledge/answers` |
| GET | `/api/history` |
| GET | `/api/history/{session_id}` |
| DELETE | `/api/history` |
| DELETE | `/api/history/{session_id}` |
| GET | `/api/system/gpu` |
| GET | `/api/system/inference` |
| GET | `/api/system/runtime-target` |

For exact request and response details, use [API_REFERENCE.md](API_REFERENCE.md).  
For current upload/API threat notes, use [SECURITY.md](SECURITY.md).
