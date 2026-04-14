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

### CI triage order

When merge-blocking CI is red, clear the gates in this order instead of mixing backend and desktop failures together:

- `backend-fast`: treat changed-files `ruff format --check` and repo-wide `ruff check` as the first blocker; when this job is red, deeper backend results are still hidden
- `backend-heavy`: after `backend-fast` is green, inspect dependency audit, import-layer lint, RAG regression, API contract sync, OTel enabled-path tests, the observability asset contract, full `pytest`, and the PR latency gate
- desktop gates: only after backend is green should triage move to `desktop-package-windows`; use `desktop-supply-chain` only for the Linux supply-chain gate or a manual `workflow_dispatch` smoke check

### SQLite schema migrations (Phase 13 Section 13.0)

On startup, `log_service.init_db` runs **`backend/services/db_migrations.apply_migrations`**, which executes `backend/migrations/NNN_*.sql` in order and records each file's SHA-256 in the `schema_migrations` table. If a migration file changes after apply, the process **refuses to start** on checksum mismatch. Add new DDL only as a new numbered SQL file.

API error responses use a stable envelope (`detail`, `code`, optional `request_id`); see [API_ERRORS.md](../api/API_ERRORS.md).

Frontend:

```bash
cd frontend
npm ci
npm run lint
npm run depcruise
npm run contract:check
npx playwright install --with-deps chromium
npm run test:e2e
npm run build
npm run bundle:check
npm run dev
```

If the backend is protected with `GOAT_API_KEY` or `GOAT_REQUIRE_SESSION_OWNER=1`
and browser login is disabled, open the browser UI settings menu and
populate `Protected access` with the shared API key and, when required, the
owner ID. The SPA stores those values locally in the browser and attaches
`X-GOAT-API-Key` / `X-GOAT-Owner-Id` to runtime API calls.
If shared-password browser login or account browser login is enabled, the browser UI
instead bootstraps `GET /api/auth/session`, shows the appropriate login gate, and
stores access in HttpOnly signed cookies; the public UI no longer needs a manually
entered owner id.
Frontend API contract types are generated from `docs/api/openapi.json`; refresh them
with `npm run contract:generate` whenever the backend contract changes.
`npm run depcruise` exercises the frontend-only import-direction and cycle guardrails for
the current app structure.

Permanent contributor policy for code placement, contract boundaries, and required
change-time gates lives in [ENGINEERING_STANDARDS.md](../standards/ENGINEERING_STANDARDS.md).

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
- `desktop-package-windows` also runs `python -m tools.desktop.packaged_shell_fault_smoke` so packaged startup stays fail-closed for missing-sidecar, early-exit-before-ready, and health-timeout paths
- `desktop-package-windows` is still the PR packaged-binary gate only; it does not install MSI/NSIS artifacts
- `desktop-package-windows` should trigger for desktop build inputs, not just Rust shell files: `frontend/src/**`, `frontend/public/**`, `frontend/index.html`, Vite/Tailwind/PostCSS/TS config, desktop scripts, desktop tooling, and desktop governance tests/workflows are part of the packaged-build truth set
- non-desktop-only backend or documentation changes should not burn the Windows packaged PR gate when they do not affect the packaged desktop build surface
- `desktop-supply-chain` now also builds Linux packaged desktop artifacts and
  retains `desktop-linux-ci-provenance.json` plus packaged `AppImage` / `deb`
  artifacts for CI-parity diagnostics; it can also be launched manually through
  `workflow_dispatch` when you need a targeted CLI check
- the `desktop-windows-fault-smoke` artifact should contain at least `build.log`, `packaged-shell-fault-smoke.log`, top-level `summary.json`, and per-scenario logs/result JSON so packaged PR failures stay diagnosable without rerunning the workflow
- when the Windows package build succeeds, CI should still retain packaged installers plus `desktop-windows-ci-provenance.json` even if the packaged fault smoke fails later in the same job
- `desktop-supply-chain` remains the Linux sidecar/provenance/cargo-audit gate; it does not own the Windows pre-ready retry semantics, and it can be triggered manually for targeted validation when needed
- `.github/workflows/desktop-provenance.yml` now runs `python -m tools.desktop.installed_windows_desktop_fault_smoke` against both the built `.msi` and NSIS installers before release assets are uploaded, and the NSIS pass still runs if the MSI pass fails first
- `.github/workflows/fault-injection.yml` reruns the same installed Windows drill on a schedule so installer regressions do not hide behind release-only evidence, and it also preserves the second installer path when the first one fails
- installed Windows evidence now writes `summary.json` even on install or scenario failure, including installer kind/path/digest, install root, log paths, partial scenario results, uninstall outcome, workflow metadata such as release ref, resolved SHA, and distribution channel, plus `primary_failure_phase` / `primary_failure_error` when uninstall failure is secondary
- installed Windows evidence now follows a fixed order: `install -> healthy launch -> fault scenarios -> uninstall`; the retained `healthy_launch` payload is the positive proof that the installed desktop reached `/api/health` and `/api/ready` before the pre-ready fault scenarios begin
- the healthy installed-launch probe uses isolated appdata, a reserved localhost backend port, preserved shell logs, and `GOAT_READY_SKIP_OLLAMA_PROBE=1` so the evidence proves installed desktop startup baseline, not local Ollama availability
- installed Windows evidence upload should use `if: always()` in both release and scheduled workflows so `desktop-installed-smoke/*/summary.json` survives the exact failures it is meant to diagnose
- PyInstaller is **not** a cross-compiler; build each platform's sidecar on that platform (or an equivalent CI runner / VM)
- on Windows developer machines, Linux-targeted desktop validation should still run from WSL when you need Linux parity; Windows-native packaging remains a Windows flow
- packaged desktop builds move app-owned writable state out of the repository and into the platform app-local-data directory

Desktop sidecar writable paths:

- SQLite DB: `<app_local_data_dir>/chat_logs.db`
- persisted app data: `<app_local_data_dir>/data`
- packaged desktop shell diagnostics now append to `<app_log_dir>/desktop-shell.log`

Packaged desktop runtime diagnostics should first check:

- `GET /api/system/desktop`
- `<app_log_dir>/desktop-shell.log`
- `GOAT_RUNTIME_ROOT`, `GOAT_LOG_DIR`, `GOAT_LOG_PATH`, `GOAT_DATA_DIR`
- `GOAT_SERVER_PORT`, `GOAT_LOCAL_PORT`, `GOAT_DEPLOY_TARGET=local`
- `GOAT_DESKTOP_SHELL_LOG_PATH`

Cross-platform release prerequisites, updater gates, and macOS blockers live in
[DESKTOP_DISTRIBUTION_READINESS.md](DESKTOP_DISTRIBUTION_READINESS.md).
- Tauri startup now emits explicit diagnostics when sidecar spawn fails, `/api/health` does not become ready before the window reveal timeout, or the bundled backend exits unexpectedly after startup
- before the main window is revealed, the Rust shell now allows only a small bounded sidecar restart/backoff budget; after reveal, unexpected sidecar exits still fail closed instead of silently recovering
- packaged desktop startup still fails closed instead of revealing the main window on a broken backend

Packaged desktop runtime config:

- The packaged desktop app inherits runtime configuration from the parent OS environment rather than a repo-local `.env`.
- Common runtime knobs for packaged installs are `OLLAMA_BASE_URL`, `GOAT_FEATURE_CODE_SANDBOX`, `GOAT_CODE_SANDBOX_PROVIDER`, and `GOAT_DESKTOP_BACKEND_PORT`.
- The desktop settings panel reads `/api/system/desktop` for backend URL, readiness summary, feature summary, writable paths, and the packaged shell log path when `GOAT_DESKTOP_SHELL_LOG_PATH` is present.
- Docker is the default sandbox backend for strong isolation. `localhost` is a trusted-dev fallback only and does not enforce the same network guarantees.

Desktop smoke command:

```bash
python -m tools.desktop.desktop_smoke --host 127.0.0.1 --port 62606
```

When API protection is enabled, pass `--api-key "$GOAT_API_KEY"`.

Public Windows desktop release path:

- `.github/workflows/desktop-provenance.yml` is the public signed installer workflow
- `desktop-package-windows` proves fail-closed startup for packaged CI binaries before merge; it is not installer-installed evidence
- `.github/workflows/desktop-provenance.yml` is the installed Windows evidence gate for signed MSI and NSIS artifacts, including healthy launch proof plus pre-ready fault scenarios
- `.github/workflows/fault-injection.yml` is the recurring installed Windows drill; it is neither a PR gate nor a signing workflow, and its job is drift detection rather than release signing
- local `npm run desktop:build` output remains internal/test-only unless it is rebuilt and signed through the workflow
- signed public Windows installers require `GOAT_DESKTOP_SIGNING_CERT_BASE64` and `GOAT_DESKTOP_SIGNING_CERT_PASSWORD`

## Deploy

Canonical checked-in operator assets now live under `ops/deploy/`, `ops/systemd/`, and `ops/verification/`.
Use the canonical `ops/` entrypoints directly; repository-root deploy wrappers are no longer supported.
The checked-in user-service unit now lives at `ops/systemd/goat-ai.service`.
The school-only variant lives at `ops/systemd/goat-ai.school-ubuntu.service`.
The checked-in reverse-proxy starter for `goat-api.duckdns.org` now lives at `ops/deploy/nginx.goat-api.duckdns.org.conf`.

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
- the checked-in Linux-facing service and `nohup` fallback now bind the backend to `127.0.0.1:62606`; publish `80/443` through a reverse proxy such as the checked-in `nginx.goat-api.duckdns.org.conf`
- for the Duck DNS public hostname, use `server_name goat-api.duckdns.org;` and then issue TLS with `sudo certbot --nginx -d goat-api.duckdns.org`
- Artifact-first rollback is the preferred path; ref-based rollback remains available for manual recovery. See [ROLLBACK.md](ROLLBACK.md)
- Windows deploy reuses Ollama on `127.0.0.1:11434` when available unless `OLLAMA_BASE_URL` is explicitly set
- Linux deploy no longer auto-detects or auto-starts the school `ollama-local` runtime by default; only `GOAT_USE_SCHOOL_OLLAMA_LOCAL=1` or `GOAT_OLLAMA_PROFILE=school-ubuntu` enables the school-specific helper script path
- When the school profile is enabled, `ops/deploy/deploy.sh` now prefers `.env.school-ubuntu` for `GOAT_USE_SCHOOL_OLLAMA_LOCAL`, `GOAT_OLLAMA_PROFILE`, and `OLLAMA_BASE_URL`, tries `goat-ai.school-ubuntu` before the generic `goat-ai` unit, and passes the resolved Ollama env vars through the `nohup` fallback too
- Deploy now includes a post-deploy contract check (`tools/ops/post_deploy_check.py`) before success is reported: it exercises `GET /api/health`, `GET /api/ready`, `GET /api/system/runtime-target`, and a short `POST /api/chat` stream. The chat step passes when the SSE body includes **at least one** `token` or **`thinking`** frame (so thinking-first models still validate), and fails on HTTP errors, empty SSE, or a first-frame `error`

Windows PowerShell deploy remains fully supported. Use WSL only when you specifically need Linux-targeted deploy-script parity or shell semantics.

### Vercel-hosted frontend split deployment

When the frontend is hosted on Vercel and FastAPI remains on a Linux host, use
[VERCEL_FRONTEND_DEPLOY.md](VERCEL_FRONTEND_DEPLOY.md) as the canonical runbook.
That path keeps browser requests same-origin at `goat-dev.vercel.app/api/*` and lets
Vercel rewrite `/api/*` to `https://goat-api.duckdns.org/api/*`.
For the public site, enable browser login on the backend instead of
publishing `X-GOAT-Owner-Id` controls in the browser UI.

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

### Simon school Ubuntu server profile

The checked-in `scripts/ollama/*local*.sh` helpers and the sibling `ollama-local` runtime
layout are now **school-only opt-in assets**, not part of the generic deploy path.

- use `GOAT_USE_SCHOOL_OLLAMA_LOCAL=1` or `GOAT_OLLAMA_PROFILE=school-ubuntu`
- keep `OLLAMA_BASE_URL=http://127.0.0.1:11435` in the school server's `.env.school-ubuntu` or another dedicated `EnvironmentFile`
- use `ops/systemd/goat-ai.school-ubuntu.service` when the school host should start the local Ollama helper automatically
- leave the generic `ops/systemd/goat-ai.service` and default deploy flow on the standard Ollama address instead

The full school-only runbook lives in [SCHOOL_UBUNTU_SERVER.md](SCHOOL_UBUNTU_SERVER.md).

## Key environment variables

Persisted blobs now flow through the configured object store. With
`GOAT_OBJECT_STORE_BACKEND=local`, objects live under `GOAT_OBJECT_STORE_ROOT`
(defaulting to `GOAT_DATA_DIR`). With `GOAT_OBJECT_STORE_BACKEND=s3`, blob payloads
live in the configured bucket/prefix while SQLite metadata remains local.

| Variable | Purpose | Default |
|----------|---------|---------|
| `OLLAMA_BASE_URL` | Ollama HTTP base URL | `http://127.0.0.1:11434` |
| `GOAT_PUBLIC_MODEL_ALLOWLIST` | Optional comma-separated override for the deployment model allowlist; default public policy is `qwen3:4b,llama3.2:3b,gemma3:4b,qwen2.5-coder:3b,gemma4:26b` | default fixed list |
| `GOAT_USE_SCHOOL_OLLAMA_LOCAL` | Explicitly opt into the school Ubuntu `ollama-local` helper/runtime path | `0` |
| `GOAT_OLLAMA_PROFILE` | Optional named profile alias; `school-ubuntu` enables the same school-only path | empty |
| `OLLAMA_GENERATE_TIMEOUT` | LLM request timeout seconds | `120` |
| `OLLAMA_CHAT_FIRST_EVENT_TIMEOUT` | `/api/chat` first SSE event timeout seconds | `90` |
| `GOAT_MAX_UPLOAD_MB` | Max upload size | `20` |
| `GOAT_MAX_DATAFRAME_ROWS` | Max parsed rows | `50000` |
| `GOAT_SYSTEM_PROMPT` | Override system prompt | built-in default |
| `GOAT_SYSTEM_PROMPT_FILE` | Path to UTF-8 prompt file | empty |
| `GOAT_LOG_PATH` | SQLite path | `<project>/var/chat_logs.db` |
| `GOAT_RUNTIME_METADATA_BACKEND` | Runtime metadata backend: `sqlite` or `postgres`; `postgres` is a hosted/server-only Phase 16D path while local and desktop remain SQLite by default | `sqlite` |
| `GOAT_RUNTIME_POSTGRES_DSN` | Required only when `GOAT_RUNTIME_METADATA_BACKEND=postgres`; used by Alembic startup schema upgrade plus hosted/server Postgres repositories | empty |
| `GOAT_DATA_DIR` | Local runtime data root; also the default local object-store root when `GOAT_OBJECT_STORE_ROOT` is unset | `<project>/var/data` (gitignored by default; do not commit) |
| `GOAT_OBJECT_STORE_BACKEND` | Blob/object-store backend for uploads, media, artifacts, normalized knowledge payloads, and workspace export files: `local` or `s3` | `local` |
| `GOAT_OBJECT_STORE_ROOT` | Local object-store root when backend=`local`; defaults to `GOAT_DATA_DIR` | `<project>/var/data` |
| `GOAT_OBJECT_STORE_BUCKET` | Required bucket when backend=`s3` | empty |
| `GOAT_OBJECT_STORE_PREFIX` | Optional key prefix inside the configured bucket | empty |
| `GOAT_OBJECT_STORE_ENDPOINT_URL` | Optional S3-compatible endpoint override | empty |
| `GOAT_OBJECT_STORE_REGION` | Optional region for the S3 client/session | empty |
| `GOAT_OBJECT_STORE_ACCESS_KEY_ID` | Optional access key id for the `s3` backend | empty |
| `GOAT_OBJECT_STORE_SECRET_ACCESS_KEY` | Optional secret access key for the `s3` backend | empty |
| `GOAT_OBJECT_STORE_S3_ADDRESSING_STYLE` | S3 addressing mode: `auto`, `path`, or `virtual` | `auto` |
| `GOAT_API_KEY` | Protect non-health APIs via `X-GOAT-API-Key` | empty |
| `GOAT_API_KEY_WRITE` | Optional second key: `GET`/`HEAD`/`OPTIONS` may use read key (`GOAT_API_KEY`); other methods require this write key when set | empty |
| `GOAT_API_CREDENTIALS_JSON` | Optional JSON credential registry; each entry may provide `secret` or `secret_sha256`, and when empty the app derives default read/write credentials from `GOAT_API_KEY` and `GOAT_API_KEY_WRITE` | empty |
| `GOAT_SHARED_ACCESS_PASSWORD_HASH` | Preferred `pwdlib` hash for the shared site password on public browser deployments | empty |
| `GOAT_SHARED_ACCESS_PASSWORD` | Legacy plaintext fallback for the shared site password; avoid in production when `GOAT_SHARED_ACCESS_PASSWORD_HASH` can be used instead | empty |
| `GOAT_SHARED_ACCESS_SESSION_SECRET` | Required signing secret for `goat_access_session` cookies when shared browser access is enabled | empty |
| `GOAT_SHARED_ACCESS_SESSION_TTL_SEC` | Browser-session cookie TTL in seconds for shared browser access | `2592000` |
| `GOAT_ACCOUNT_AUTH_ENABLED` | Enables browser account login alongside or instead of the shared password flow | `false` |
| `GOAT_BROWSER_SESSION_SECRET` | Required signing secret for `goat_account_session` and Google OAuth state cookies when account browser auth is enabled | empty |
| `GOAT_ACCOUNT_SESSION_TTL_SEC` | Browser-session cookie TTL in seconds for account login | `2592000` |
| `GOOGLE_CLIENT_ID` | Google OAuth client id for browser account login | empty |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret for browser account login | empty |
| `GOOGLE_REDIRECT_URI` | Frontend callback URI that receives the Google OAuth authorization code | empty |
| `GOAT_GOOGLE_OAUTH_STATE_TTL_SEC` | Google OAuth state-cookie TTL in seconds | `600` |
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

### Object storage modes (Phase 16C) and hosted runtime metadata (Phase 16D)

- Runtime metadata stays at `GOAT_LOG_PATH` for local and desktop by default; hosted/server deployments may opt into Postgres while Phase 16C continues to own only the binary/object payload boundary.
- `GOAT_RUNTIME_METADATA_BACKEND=sqlite` remains the default runtime metadata mode, and local or desktop binaries stay on SQLite in the shipped app.
- `GOAT_RUNTIME_METADATA_BACKEND=postgres` is a server-only hosted runtime mode. It requires `GOAT_DEPLOY_TARGET=server` plus `GOAT_RUNTIME_POSTGRES_DSN`, applies Alembic schema upgrades at startup through the same path exposed by `python -m tools.ops.upgrade_runtime_postgres_schema`, and is intended to be cut over only after `python -m tools.ops.export_runtime_metadata_snapshot`, `python -m tools.ops.import_runtime_metadata_snapshot`, and `python -m tools.ops.check_runtime_metadata_parity` succeed against the same restore set.
- Runtime metadata snapshots now include `auth_users` and `auth_user_identities` when account login is enabled; treat every snapshot/backup that contains these tables as sensitive because it carries password hashes and external identity bindings.
- `GOAT_OBJECT_STORE_BACKEND=local` keeps knowledge uploads, normalized payloads, vector payload JSON, media attachments, generated artifacts, and workspace-export files on the host filesystem under `GOAT_OBJECT_STORE_ROOT`.
- `GOAT_OBJECT_STORE_BACKEND=s3` moves the same payload families behind an S3-compatible object-store contract. The backend environment must include `boto3` for this mode.
- Read compatibility is preserved for older local files under `GOAT_DATA_DIR/uploads/*` and `GOAT_DATA_DIR/vector_index/*` while SQLite rows still reference legacy paths.
- Backup, restore, and rollback should treat the SQLite snapshot plus the matching object-store snapshot as one recovery unit; hosted/server Postgres cutover additionally requires the imported runtime metadata snapshot and a clean parity pass from the same capture window.
- The canonical application/storage contract lives in [OBJECT_STORAGE_CONTRACT.md](../architecture/OBJECT_STORAGE_CONTRACT.md).

### Code sandbox operations (Phase 18)

- `POST /api/code-sandbox/exec` now performs real provider-backed execution when:
  - `GOAT_FEATURE_CODE_SANDBOX=1`
  - the selected provider probe succeeds
  - the caller credential includes `sandbox:execute`
- Phase 18A remains intentionally conservative:
  - `sync` is the default; `async` uses in-process dispatch plus startup
    recovery that replays `queued` executions and fails abandoned `running`
    executions closed
  - short-lived execution only
  - one shell-capable preset
  - Docker enforces `network_policy=disabled` by default; `localhost` reports a degraded contract and does not enforce the same network boundary
  - `docker`: no privileged mode and no host Docker socket mounted into the sandbox container
  - `localhost`: intended for trusted local development only; it does not provide Docker-grade isolation
- visible `queued` and `running` executions can be cancelled through the
  existing cancel route; running cancellation remains cooperative and returns a
  conflict if the execution does not acknowledge within the bounded API wait
  window
- The execution contract persists durable rows, event timelines, and replayable log chunks in SQLite:
  - `GET /api/code-sandbox/executions/{execution_id}`
  - `GET /api/code-sandbox/executions/{execution_id}/events`
  - `GET /api/code-sandbox/executions/{execution_id}/logs`
- `GET /api/code-sandbox/executions/{execution_id}/logs` is an SSE stream for stdout/stderr replay plus status updates; clients may reconnect with `after_seq=<last_seen_log_sequence>`
- Files written under `outputs/` are surfaced as metadata in the API response, but they are not yet promoted into the artifact workspace model.
- Each workspace also gets `.goat/workspace_manifest.json` and the
  `GOAT_SANDBOX_EXECUTION_ID`, `GOAT_SANDBOX_WORKSPACE`,
  `GOAT_SANDBOX_OUTPUTS_DIR`, `GOAT_SANDBOX_MANIFEST`, and
  `GOAT_SANDBOX_NETWORK_POLICY` environment variables so scripts can discover
  their runtime context without guessing local paths.

### OpenTelemetry (optional, Phase 15.6)

- Default **`GOAT_OTEL_ENABLED=0`** - tracing is off; the app does not eagerly import the OpenTelemetry SDK.
- Set **`GOAT_OTEL_ENABLED=1`** to enable a `TracerProvider`, W3C **`traceparent`** / **`tracestate`** extraction on incoming HTTP requests (`backend/platform/otel_middleware.py`), and spans around Ollama HTTP calls in `goat_ai/llm/ollama_client.py`.
- **`GOAT_OTEL_EXPORTER`:** `console` (default) prints spans to stderr; `otlp` sends to **`OTEL_EXPORTER_OTLP_ENDPOINT`** (OTLP/HTTP traces URL, e.g. `http://127.0.0.1:4318/v1/traces`).
- `backend-heavy` now runs explicit OTel enabled-path tests so provider init, `traceparent` propagation, OTLP fallback, and middleware registration stay proven instead of default-off-only.
- Standard OpenTelemetry env vars apply alongside the above (see OpenTelemetry Python docs for OTLP tuning).

### Structured logging (Phase 13 Wave A)

- Inbound `X-Request-ID` is honored; otherwise the server assigns one. It is bound for the request in a context var and appears on log lines and JSON error bodies.
- With `GOAT_LOG_JSON=1`, root logs are JSON objects. Access-style lines from `goat_ai.access` include `route`, `status`, and `duration_ms`.
- Error responses from exception handlers include the same `X-Request-ID` used for log correlation.

Example line:

```json
{"ts": "2026-04-07 12:00:00,000", "level": "INFO", "logger": "goat_ai.access", "message": "http_request", "request_id": "550e8400-e29b-41d4-a716-446655440000", "route": "/api/history", "status": 200, "duration_ms": 2.145}

### Credential-backed authorization (historical authz 16C)

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

### Browser login modes for public deployments

Use browser login when a public browser deployment should stay behind either a
shared site password, stable user accounts, or both, while keeping
history/artifacts/media/workbench data aligned with the existing caller-scoped
authorization model.

Shared-password configuration:

- set `GOAT_SHARED_ACCESS_PASSWORD_HASH` to a `pwdlib` hash of the public site password
- set `GOAT_SHARED_ACCESS_SESSION_SECRET` to a long random signing secret
- optionally tune `GOAT_SHARED_ACCESS_SESSION_TTL_SEC` (default `2592000`, or 30 days)

Account-login configuration:

- set `GOAT_ACCOUNT_AUTH_ENABLED=1`
- set `GOAT_BROWSER_SESSION_SECRET` to a long random signing secret for `goat_account_session`
- optionally tune `GOAT_ACCOUNT_SESSION_TTL_SEC` (default `2592000`, or 30 days)
- pre-provision local accounts with `python -m tools.ops.create_local_account --email user@example.com`

Optional Google OAuth configuration:

- set all of `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REDIRECT_URI`
- set `GOAT_GOOGLE_OAUTH_STATE_TTL_SEC` only if you need a non-default state-cookie TTL
- add the same frontend callback origin or path to the Google Console redirect URI allow-list

Generate the shared-password hash with:

```bash
python -c "from pwdlib import PasswordHash; print(PasswordHash.recommended().hash('replace-with-a-site-password'))"
```

Runtime behavior:

- `GET /api/auth/session` and `POST /api/auth/logout` remain public so the SPA can bootstrap and recover
- `POST /api/auth/login` issues `goat_access_session` for shared-password browser mode
- `POST /api/auth/account/login` and `POST /api/auth/account/google` issue `goat_account_session` for stable user mode
- `GET /api/auth/account/google/url` issues the short-lived `goat_google_oauth_state` cookie used to bind the OAuth callback to the same browser
- successful login in one browser mode clears the other browser-mode cookies so the browser stays on one active login path at a time
- shared-password login creates a fresh browser-specific owner id per login; account login resolves to stable owner ids of the form `user:<user_id>`
- all other `/api` routes require either a valid browser session cookie or a valid API key
- auth-sensitive `GET` routes and artifact downloads return `Cache-Control: no-store` and `Vary: Cookie, X-GOAT-API-Key, X-GOAT-Owner-Id`

Minimum rollout order:

1. Decide whether the deployment should expose shared password, account login, or both.
2. Set the matching env vars and restart the backend.
3. Verify `curl -i https://<backend>/api/auth/session` returns `200` with `auth_required=true` plus the expected `available_login_methods`.
4. If shared-password mode is newly enabled, dry-run the ownerless history cleanup:

   ```bash
   python -m tools.ops.purge_ownerless_history
   ```

5. Execute the cleanup after reviewing the matched session ids:

   ```bash
   python -m tools.ops.purge_ownerless_history --execute
   ```

6. If account login is enabled, create at least one local test account:

   ```bash
   python -m tools.ops.create_local_account --email user@example.com
   ```

7. If Google OAuth is enabled, confirm the configured `GOOGLE_REDIRECT_URI` matches the frontend origin/path exactly.
8. Smoke-test:
   - two clean browser profiles using the same shared password cannot see each other's `/api/history` rows
   - the same account can sign in from two browsers and see the same stable history
   - invalid Google state or token returns `401` with `AUTH_INVALID_GOOGLE_STATE` or `AUTH_INVALID_GOOGLE_TOKEN`

### Authorization audit events (historical authz 16C)

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
- `backend/platform/prometheus_metrics.py::EXPORTED_METRIC_FAMILIES` is the single source of truth for operator-facing metric families.
- Operator-facing metric families currently shipped from that contract are:
  - `http_requests_total`
  - `http_request_duration_seconds`
  - `chat_stream_completed_total`
  - `ollama_errors_total`
  - `sqlite_log_write_failures_total`
  - `feature_gate_denials_total`
  - `knowledge_retrieval_requests_total`
  - `knowledge_query_rewrite_applied_total`
- Versioned observability assets live under [`ops/observability/`](../../ops/observability/README.md):
  - Prometheus scrape example: [`ops/observability/prometheus/goat-api-scrape.yml`](../../ops/observability/prometheus/goat-api-scrape.yml)
  - Alert rules: [`ops/observability/alerts/goat-api-alerts.yml`](../../ops/observability/alerts/goat-api-alerts.yml)
  - Grafana dashboard: [`ops/observability/grafana/goat-api-dashboard.json`](../../ops/observability/grafana/goat-api-dashboard.json)
- `backend-heavy` also runs an observability asset contract so alerts, dashboards, and runbooks cannot reference metric families that the API no longer exports, and every exported family must remain covered by at least one approved observability surface.
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

**Regression helper:** `python -m tools.quality.run_rag_eval` (from the repository root)
exercises the retrieval-quality golden set and matches the backend CI proof surface.

**Knobs (environment + request):**

| Control | Where | Behavior |
|---------|--------|----------|
| `GOAT_RAG_RERANK_MODE` | `passthrough` or `lexical` | For `retrieval_profile=default` only, selects vector order vs lexical overlap rerank after the vector stage (`goat_ai/config/settings.py`). |
| `retrieval_profile` | `POST /api/knowledge/search` body | `default` - uses `GOAT_RAG_RERANK_MODE`; `rag3_lexical` / `rag3_quality` - always lexical rerank; `rag3_quality` also enables conservative whitespace query rewrite before search. |
| Vector similarity | Implementation | Scores are backend-specific; there is **no** global numeric score threshold in config-triage uses **hit vs miss** (see metrics) and eval cases. |

**No-hit behavior:** search returns zero citations when nothing ranks above the empty list; `POST /api/knowledge/answers` now returns a brief synthesized insufficiency answer plus an empty citation list when no hits remain after the optional attached-document fallback.

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
- If the rollback is caused by a schema, data, or object-store regression, pair it with [BACKUP_RESTORE.md](BACKUP_RESTORE.md)
- Phase 16C means uploads, media, knowledge payloads, and generated artifacts may require a matched SQLite + object-store restore set instead of a code-only rollback

## Backup and restore

- Runbook: [BACKUP_RESTORE.md](BACKUP_RESTORE.md)
- SQLite metadata backup:

```bash
python -m tools.ops.backup_chat_db
```

- Phase 16C note: `python -m tools.ops.backup_chat_db` backs up SQLite metadata only; object payloads must be captured from `GOAT_OBJECT_STORE_ROOT` or the configured bucket/prefix during the same maintenance window

- Recovery drill:

```bash
python -m tools.ops.exercise_recovery_drill --src "$GOAT_LOG_PATH" --backup-dir ./backups --required-table sessions --required-table session_messages
```

- Use the recovery drill when validating backup/restore readiness or when checking a
host's ability to recover from a bad SQLite state.
- When `GOAT_OBJECT_STORE_BACKEND=local`, snapshot `GOAT_OBJECT_STORE_ROOT`
  alongside the SQLite backup so `storage_key` references still resolve after restore.
- When `GOAT_OBJECT_STORE_BACKEND=s3`, pair the SQLite backup with a matching
  bucket/prefix snapshot or versioned restore point; deploy rollback does not restore
  remote objects by itself.

## GPU and telemetry

Telemetry endpoints:

- `GET /api/system/gpu`
- `GET /api/system/inference`

If `nvidia-smi` is unavailable or unreadable, GPU telemetry should degrade gracefully instead of showing fake values.

## Operational stop signs

Treat the following as operational stop signs during runtime, persistence, or rollout changes:

| Trigger | Response |
|---------|----------|
| Repeated SSE failure or timeout in post-deploy contract checks | Pause Wave B work, inspect `var/logs/fastapi.log` and Ollama logs, and do not advance the rollout until `/api/chat` emits SSE again. |
| `/api/ready` flapping or sustained non-200 responses | Block broader structural or rollout changes until readiness and deploy checks are stable across a full deploy cycle. |
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
