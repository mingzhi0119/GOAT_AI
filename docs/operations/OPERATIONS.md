# GOAT AI Operations

## Runtime targets

- Local development backend: `:62606`
- Frontend dev server: `:3000`
- Production server target: `:62606`
- Runtime target API: `GET /api/system/runtime-target`

Runtime target resolution now follows a single-port policy: always `GOAT_SERVER_PORT` (default `62606`), with no `8002` fallback.

## WSL on Windows

Windows-native development remains supported. Use WSL selectively when you need Linux semantics that should match Ubuntu CI or production behavior.

Common WSL-triggering cases:

- Linux-targeted compile or package validation
- shell-script verification
- Ubuntu CI parity checks
- Linux desktop sidecar and Tauri/Linux validation
- cases where a dependency or wheel is awkward on Windows but straightforward in Linux

Use [WSL_DEVELOPMENT.md](WSL_DEVELOPMENT.md) for the selective WSL workflow guidance and example commands.

## Development

Backend:

```bash
python3.14 -m venv .venv   # use Python 3.14 when available (matches CI; see `.github/workflows/ci.yml`)
source .venv/bin/activate
pip install -r requirements-ci.txt
cp .env.example .env
lint-imports
python3 -m uvicorn server:create_app --factory --host 0.0.0.0 --port 62606 --reload
```

`lint-imports` enforces backend package layering (`pyproject.toml`); run it after dependency or router/service refactors.

**Repository tools:** run CLI modules from the **repository root** with `python -m tools.<module>` (for example `python -m tools.quality.run_rag_eval`, `python -m tools.contracts.check_api_contract_sync`). This avoids setting `PYTHONPATH` manually; `.env` is for app runtime, not your shell. For **`python -m tools.contracts.check_api_contract_sync`**, use the **same Python minor as CI (3.14)** so `docs/api/openapi.json` matches `app.openapi()`. On Windows hosts, use WSL when a tool or dependency path needs Linux parity. `bash scripts/wsl/wsl_api_contract_refresh.sh` remains the preferred artifact-refresh path when Windows packaging availability differs from CI.

### SQLite schema migrations (Phase 13 Section 13.0)

On startup, `log_service.init_db` runs **`backend/services/db_migrations.apply_migrations`**, which executes `backend/migrations/NNN_*.sql` in order and records each file's SHA-256 in the `schema_migrations` table. If a migration file changes after apply, the process **refuses to start** on checksum mismatch. Add new DDL only as a new numbered SQL file.

API error responses use a stable envelope (`detail`, `code`, optional `request_id`); see [API_ERRORS.md](../api/API_ERRORS.md).

Frontend:

```bash
cd frontend
npm ci
npm run lint
npm run contract:check
npx playwright install --with-deps chromium
npm run test:e2e
npm run build
npm run bundle:check
npm run dev
```

If the backend is protected with `GOAT_API_KEY` or `GOAT_REQUIRE_SESSION_OWNER=1`,
open the browser UI settings menu and populate `Protected access` with the shared
API key and, when required, the owner ID. The SPA stores those values locally in
the browser and attaches `X-GOAT-API-Key` / `X-GOAT-Owner-Id` to runtime API calls.
Frontend API contract types are generated from `docs/api/openapi.json`; refresh them
with `npm run contract:generate` whenever the backend contract changes.

### Windows desktop prerequisites

This remains a normal Windows-native flow for the Tauri-based desktop shell and future packaged Windows app path. Use the bootstrap script instead of manually clicking through installers:

```powershell
.\scripts\desktop\install_desktop_prereqs.ps1 -Profile Runtime
.\scripts\desktop\install_desktop_prereqs.ps1 -Profile Dev
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
python -m tools.desktop.build_desktop_sidecar
cd frontend
npm run desktop:build
```

Important notes:

- `python -m tools.desktop.build_desktop_sidecar` builds a per-platform executable with **PyInstaller**
- the output is copied to `frontend/src-tauri/binaries/goat-backend-$TARGET_TRIPLE[.exe]`
- `npm run desktop:build` triggers the same sidecar build automatically through Tauri's `beforeBuildCommand`
- merge-blocking CI now also builds real Windows packaged desktop installers and records provenance through `python -m tools.desktop.write_desktop_release_provenance`
- PyInstaller is **not** a cross-compiler; build each platform's sidecar on that platform (or an equivalent CI runner / VM)
- on Windows developer machines, Linux-targeted desktop validation should still run from WSL when you need Linux parity; Windows-native packaging remains a Windows flow
- packaged desktop builds move app-owned writable state out of the repository and into the platform app-local-data directory

Desktop sidecar writable paths:

- SQLite DB: `<app_local_data_dir>/chat_logs.db`
- persisted app data: `<app_local_data_dir>/data`
- packaged desktop shell diagnostics now append to `<app_log_dir>/desktop-shell.log`
- Tauri startup now emits explicit diagnostics when sidecar spawn fails, `/api/health` does not become ready before the window reveal timeout, or the bundled backend exits unexpectedly after startup
- packaged desktop startup now fails closed instead of revealing the main window on a broken backend

Packaged desktop runtime config:

- The packaged desktop app inherits runtime configuration from the parent OS environment rather than a repo-local `.env`.
- Common runtime knobs for packaged installs are `OLLAMA_BASE_URL`, `GOAT_FEATURE_CODE_SANDBOX`, `GOAT_CODE_SANDBOX_PROVIDER`, and `GOAT_DESKTOP_BACKEND_PORT`.
- Docker is the default sandbox backend for strong isolation. `localhost` is a trusted-dev fallback only and does not enforce the same network guarantees.

Desktop smoke command:

```bash
python -m tools.desktop.desktop_smoke --host 127.0.0.1 --port 62606
```

When API protection is enabled, pass `--api-key "$GOAT_API_KEY"`.

Public Windows desktop release path:

- `.github/workflows/desktop-provenance.yml` is the public signed installer workflow
- local `npm run desktop:build` output remains internal/test-only unless it is rebuilt and signed through the workflow
- signed public Windows installers require `GOAT_DESKTOP_SIGNING_CERT_BASE64` and `GOAT_DESKTOP_SIGNING_CERT_PASSWORD`

## Deploy

Canonical checked-in operator assets now live under `ops/deploy/`, `ops/systemd/`, and `ops/verification/`.
Use the canonical `ops/` entrypoints directly; repository-root deploy wrappers are no longer supported.
The checked-in user-service unit now lives at `ops/systemd/goat-ai.service`.

Linux:

```bash
bash ops/deploy/deploy.sh
QUICK=1 bash ops/deploy/deploy.sh
SKIP_BUILD=1 bash ops/deploy/deploy.sh
SYNC_GIT=1 bash ops/deploy/deploy.sh
RELEASE_BUNDLE=/tmp/release-bundle.tar.gz RELEASE_MANIFEST=/tmp/release-manifest.json bash ops/deploy/deploy.sh
```

Windows PowerShell:

```powershell
.\ops\deploy\deploy.ps1
.\ops\deploy\deploy.ps1 -Quick
.\ops\deploy\deploy.ps1 -SkipBuild
.\ops\deploy\deploy.ps1 -SyncGit
```

Important behavior:

- Deploy defaults to the current checkout
- `SYNC_GIT=1` is explicit opt-in
- `GIT_REF` is authoritative: branch refs sync to `origin/$GIT_REF`, while tag/commit refs deploy in detached mode without drifting back to `main`
- `EXPECTED_GIT_SHA` may be supplied by release automation to hard-fail if the host resolves any SHA other than the requested release commit
- `RELEASE_BUNDLE` + `RELEASE_MANIFEST` switch deploy into artifact-first mode: the shipped bundle is installed before process restart, and the host no longer rebuilds the frontend from source
- `deploy.sh` keeps the `nohup` + `var/logs/fastapi.pid` fallback path
- `ops/deploy/deploy.sh` and `ops/deploy/deploy.ps1` now stop the current FastAPI process gracefully first, then force cleanup only if the drain window expires
- Artifact-first rollback is the preferred path; ref-based rollback remains available for manual recovery. See [ROLLBACK.md](ROLLBACK.md)
- Windows deploy reuses Ollama on `127.0.0.1:11434` when available unless `OLLAMA_BASE_URL` is explicitly set
- Deploy now includes a post-deploy contract check (`tools/ops/post_deploy_check.py`) before success is reported: it exercises `GET /api/health`, `GET /api/ready`, `GET /api/system/runtime-target`, and a short `POST /api/chat` stream. The chat step passes when the SSE body includes **at least one** `token` or **`thinking`** frame (so thinking-first models still validate), and fails on HTTP errors, empty SSE, or a first-frame `error`

Windows PowerShell deploy remains fully supported. Use WSL only when you specifically need Linux-targeted deploy-script parity or shell semantics.

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
| `GOAT_LOG_PATH` | SQLite path | `<project>/var/chat_logs.db` |
| `GOAT_DATA_DIR` | Root directory for persisted uploads, normalized knowledge text, vector indexes, and vision attachments | `<project>/var/data` (gitignored by default; do not commit) |
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
| `GOAT_FEATURE_AGENT_WORKBENCH` | Operator exposes the shared workbench feature family; actual sub-capability readiness still depends on runtime support (`plan`, `browse`, `deep_research`, and the shipped `canvas` workspace-output baseline with session restoration, direct reopen, and export-to-artifact linkage are implemented; public-web retrieval is now experimental DDGS-backed while project memory and connectors remain open) | `0` |
| `GOAT_WORKBENCH_WEB_PROVIDER` | Public-web provider for browse/deep-research: `duckduckgo` or `disabled` | `duckduckgo` |
| `GOAT_WORKBENCH_WEB_MAX_RESULTS` | Upper bound for returned public-web results per task | `6` |
| `GOAT_WORKBENCH_WEB_TIMEOUT_SEC` | Timeout for the public-web provider request | `15` |
| `GOAT_WORKBENCH_WEB_REGION` | DDGS region hint for public-web retrieval | `wt-wt` |
| `GOAT_WORKBENCH_WEB_SAFESEARCH` | DDGS safesearch mode: `on`, `moderate`, or `off` | `moderate` |
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
- Set **`GOAT_OTEL_ENABLED=1`** to enable a `TracerProvider`, W3C **`traceparent`** / **`tracestate`** extraction on incoming HTTP requests (`backend/platform/otel_middleware.py`), and spans around Ollama HTTP calls in `goat_ai/llm/ollama_client.py`.
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
- Versioned observability assets live under [`ops/observability/`](../../ops/observability/README.md):
  - Prometheus scrape example: [`ops/observability/prometheus/goat-api-scrape.yml`](../../ops/observability/prometheus/goat-api-scrape.yml)
  - Alert rules: [`ops/observability/alerts/goat-api-alerts.yml`](../../ops/observability/alerts/goat-api-alerts.yml)
  - Grafana dashboard: [`ops/observability/grafana/goat-api-dashboard.json`](../../ops/observability/grafana/goat-api-dashboard.json)
- Checked-in deploy and verification assets live under:
  - `ops/deploy/deploy.sh`
  - `ops/deploy/deploy.ps1`
  - `ops/systemd/goat-ai.service`
  - `ops/verification/phase0_check.sh`
- First-response runbook for failures is tracked in [INCIDENT_TRIAGE.md](INCIDENT_TRIAGE.md).

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
- Application boundaries now receive idempotency storage through an injectable `IdempotencyStore` protocol so higher-scale storage can replace the SQLite adapter without rewriting router/application logic

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

**Regression:** run `python -m tools.quality.run_rag_eval` (from the repository root) before merge when changing `backend/services/retrieval_quality/`, `tools/quality/run_rag_eval.py`, or `evaldata/`. CI enforces this on every backend job.

**Knobs (environment + request):**

| Control | Where | Behavior |
|---------|--------|----------|
| `GOAT_RAG_RERANK_MODE` | `passthrough` or `lexical` | For `retrieval_profile=default` only, selects vector order vs lexical overlap rerank after the vector stage (`goat_ai/config/settings.py`). |
| `retrieval_profile` | `POST /api/knowledge/search` body | `default` - uses `GOAT_RAG_RERANK_MODE`; `rag3_lexical` / `rag3_quality` - always lexical rerank; `rag3_quality` also enables conservative whitespace query rewrite before search. |
| Vector similarity | Implementation | Scores are backend-specific; there is **no** global numeric score threshold in config-triage uses **hit vs miss** (see metrics) and eval cases. |

**No-hit behavior:** search returns zero citations when nothing ranks above the empty list; `POST /api/knowledge/answers` returns the documented fixed sentence when no hits (after optional attached-document fallback).

**Observability (`GET /api/system/metrics`):**

- `knowledge_retrieval_requests_total{retrieval_profile="...",outcome="hit|miss"}` - one increment per `search_knowledge` execution.
- `knowledge_query_rewrite_applied_total{retrieval_profile="..."}` - increments when conservative rewrite changed the query (`rag3_quality`).

**Golden set:** see [evaldata/README.md](../evaldata/README.md) and `evaldata/VERSION`.

### Multi-instance stance (honest limits)

- Rate limiting in `backend/platform/http_security.py` is still in-memory and per-process by default, but it now executes behind a replaceable `RateLimiter` boundary so a shared store can replace the current adapter without changing middleware semantics
- Rolling latency samples (`/api/system/inference`) are process-local
- Idempotency cache is SQLite-backed in this release; concurrent multi-writer behavior across many app instances is not treated as a cluster-wide guarantee
- Durable background execution now also uses a replaceable runner boundary, and workbench startup recovery explicitly replays queued tasks while marking previously running tasks as interrupted
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
| Max concurrent SSE streams (single process) | 20 | Runbook load validation (`python -m tools.quality.load_chat_smoke`) |
| Upload analyze JSON budget | <= 5 s for <= 20 MB supported knowledge file (`csv/xlsx/txt/md/pdf/docx`) | `POST /api/upload/analyze` smoke run |
| Session append guardrails | hard-stop at configured maxes | `GOAT_MAX_CHAT_MESSAGES`, `GOAT_MAX_CHAT_PAYLOAD_BYTES` |

Load smoke command:

```bash
python -m tools.quality.load_chat_smoke --base-url http://127.0.0.1:62606 --model gemma4:26b --runs 20 --show-system-inference
```

When API protection is enabled, pass `--api-key "$GOAT_API_KEY"`.

Performance governance:

- `.github/workflows/performance-nightly.yml` runs the same smoke command on a schedule or manual dispatch.
- `.github/workflows/ci.yml` now also runs `python -m tools.quality.run_pr_latency_gate` with in-process fake-LLM traffic so the highest-risk chat latency regressions fail before merge.
- The performance gate currently fails when:
  - full chat p95 exceeds `12000 ms`
  - first-token p95 exceeds `2000 ms`
- The PR latency gate currently fails when:
  - in-process chat total p95 exceeds `1200 ms`
  - in-process first-token p95 exceeds `400 ms`
- Keep those thresholds aligned with the SLO starter table unless a reviewed change updates both the workflow and this document.

## Release governance

- `.github/workflows/release-governance.yml` is the P1 release workflow for:
  - immutable bundle + release-manifest generation
  - staging deployment of the exact retained bundle
  - production promotion of the same bundle behind GitHub Environment approval
  - per-environment promotion evidence with artifact digest and rollback target capture
- `python -m tools.release.exercise_release_rollback_drill` is the repo-level artifact rollback drill for scratch-project validation of bundle promotion + rollback semantics.
- Release policy and required environment secrets are documented in [RELEASE_GOVERNANCE.md](RELEASE_GOVERNANCE.md).

## Process and health

- Liveness: `GET /api/health`
- Readiness: `GET /api/ready` (SQLite + optional Ollama probe; use `GOAT_READY_SKIP_OLLAMA_PROBE=1` when Ollama is intentionally absent)
- Logs: `var/logs/fastapi.log`
- PID file in nohup mode: `var/logs/fastapi.pid`

Stop commands:

```bash
kill "$(cat var/logs/fastapi.pid)"
```

```powershell
Stop-Process -Id (Get-Content .\var\logs\fastapi.pid)
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
python -m tools.ops.backup_chat_db
```

- Recovery drill:

```bash
python -m tools.ops.exercise_recovery_drill --src "$GOAT_LOG_PATH" --backup-dir ./backups --required-table sessions --required-table session_messages
```

- The recovery drill is now covered by automated tests; keep it passing whenever backup, restore, rollback, or SQLite persistence behavior changes.

## GPU and telemetry

Telemetry endpoints:

- `GET /api/system/gpu`
- `GET /api/system/inference`

If `nvidia-smi` is unavailable or unreadable, GPU telemetry should degrade gracefully instead of showing fake values.

## Phase 13 risk triggers

Treat the following as operational stop signs during Phase 13 rollout work:

| Trigger | Response |
|---------|----------|
| Repeated SSE failure or timeout in post-deploy contract checks | Pause Wave B work, inspect `var/logs/fastapi.log` and Ollama logs, and do not advance the rollout until `/api/chat` emits SSE again. |
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

For exact request and response details, use [API_REFERENCE.md](../api/API_REFERENCE.md).  
For current upload/API threat notes, use [SECURITY.md](../governance/SECURITY.md).
