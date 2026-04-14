# GOAT AI

Strategic Intelligence assistant for Simon Business School, University of Rochester.

- Example public deployment: <https://goat-dev.vercel.app> (frontend) with the public backend currently published at <https://goat-api.duckdns.org>
- Repo: <https://github.com/mingzhi0119/GOAT_AI>
- Current snapshot: [docs/governance/PROJECT_STATUS.md](docs/governance/PROJECT_STATUS.md)
- API contract: [docs/api/API_REFERENCE.md](docs/api/API_REFERENCE.md)
- Frontend appearance hand-off: [docs/standards/APPEARANCE.md](docs/standards/APPEARANCE.md)

## Environments

- **Portable by design:** the same repo is meant to run on **Windows, macOS, and Linux** for development, and on **various Linux (or container) server layouts** for production, not tied to a single school-owned Ubuntu image. Paths, ports, GPU selection, and secrets are **environment-driven** (see `.env.example` and [docs/operations/OPERATIONS.md](docs/operations/OPERATIONS.md)); avoid hardcoding host-specific assumptions in code.
- **Reference vs local:** the example public deployment listed above is a **reference deployment**, not a constraint on where you may install or develop.

### Windows development

Windows-native development remains a supported and normal path for this repository.

- Use native Windows tooling for the usual local inner loop when that is the most comfortable setup for you.
- Use WSL selectively when you need Linux semantics that must match Ubuntu CI or production behavior.
- Typical WSL-only or WSL-preferred cases are Linux-targeted compile/package checks, shell-script validation, Linux desktop validation, or dependency/tooling gaps on Windows.

See [docs/operations/WSL_DEVELOPMENT.md](docs/operations/WSL_DEVELOPMENT.md) for the selective WSL workflow guidance and exception list.

### Capability-based / high-risk features

Some capabilities (for example the shipped **provider-backed code execution runtime**) require explicit runtime declarations and operator review. Separate concerns:

| Concern | What it answers | Typical outcome when blocked |
|--------|-----------------|------------------------------|
| **Authorization / policy** | Is *this caller* (user, role, tenant, API key scope) allowed? | **403** + stable `code` (e.g. `FEATURE_DISABLED`) |
| **Capability / runtime** | Is *this deployment* configured and are dependencies (Docker socket, etc.) ready? | **503** + stable `code` (e.g. `FEATURE_UNAVAILABLE`) |

| Host situation | Expected behavior |
|----------------|-------------------|
| Docker (or approved runtime) available and operators enable the feature | Code sandbox runs with container isolation and enforced `network_policy=disabled` by default. |
| `localhost` provider enabled for trusted local development | Code execution is available as a host-shell fallback, but it is **not** a fully isolated sandbox and does **not** enforce the same network guarantees as Docker. |
| Operators opt out entirely | **Disable** code execution; the rest of the app (chat, RAG, uploads, downloads of **non-executed** generated files) continues to work within normal limits. |

This is now the shipped model for the Phase 18 Docker-first sandbox MVP: **high-risk operations are gated by explicit configuration and runtime readiness**, not on by default; **per-caller policy** remains separate from deployment/runtime readiness.

**Industrial implementation pattern** (config + probe + API + service enforcement + tests): see [docs/standards/ENGINEERING_STANDARDS.md](docs/standards/ENGINEERING_STANDARDS.md) **Section 15 Feature enable/disable and gating**.

## Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, Uvicorn; **Python 3.14** recommended for local dev and API artifact parity; CI backend job uses **3.14**; production hosts may still run **3.12.x** until upgraded |
| Frontend | React 19, TypeScript, Vite 8 |
| LLM runtime | Ollama |
| Data parsing | pandas, openpyxl, python-docx, pypdf |
| Persistence | SQLite |
| Charts | Apache ECharts |

## Architecture

Typical production path: **browser -> reverse proxy (e.g. nginx) -> FastAPI/Uvicorn** on a configured port (default **62606** via `GOAT_SERVER_PORT` / runtime target; see [docs/operations/OPERATIONS.md](docs/operations/OPERATIONS.md)). Local development often uses the same app process without nginx.

FastAPI serves:
- React SPA from `frontend/dist/`
- REST + SSE APIs under `/api`

Core API surface:
- `GET /api/health`
- `GET /api/ready`
- `GET /api/system/metrics`
- `GET /api/models`
- `GET /api/models/capabilities`
- `POST /api/chat`
- `POST /api/upload`
- `POST /api/upload/analyze`
- `POST /api/knowledge/uploads`
- `GET /api/knowledge/uploads/{document_id}`
- `POST /api/knowledge/ingestions`
- `GET /api/knowledge/ingestions/{ingestion_id}`
- `POST /api/knowledge/search`
- `POST /api/knowledge/answers`
- `GET /api/artifacts/{artifact_id}`
- `GET /api/history`
- `GET /api/history/{session_id}`
- `PATCH /api/history/{session_id}`
- `DELETE /api/history`
- `DELETE /api/history/{session_id}`
- `GET /api/system/gpu`
- `GET /api/system/inference`
- `GET /api/system/runtime-target`
- `GET /api/system/features` (capability-gated features: config + host probe)
- `POST /api/code-sandbox/exec` (run one durable shell sandbox execution in `sync` or `async` mode)
- `GET /api/code-sandbox/executions/{execution_id}` (read one persisted sandbox execution)
- `GET /api/code-sandbox/executions/{execution_id}/events` (read one persisted sandbox execution timeline)
- `GET /api/code-sandbox/executions/{execution_id}/logs` (stream replayable sandbox logs over SSE)
- `POST /api/workbench/tasks` (create and enqueue a durable workbench task)
- `GET /api/workbench/sources` (list declarative retrieval sources for workbench tasks)
- `GET /api/workbench/tasks/{task_id}` (poll durable task status)
- `GET /api/workbench/tasks/{task_id}/events` (read durable task event timeline)

## Current behavior

- Chat streams typed SSE event objects: `thinking` (collapsed reasoning in the UI), `token` (answer text), `chart_spec`, `artifact`, `error`, `done`
- Upload SSE ingests supported files into the knowledge pipeline and emits `knowledge_ready`, `error`, `done`
- Charts are created only from native Ollama tool calls during chat
- Session history is persisted in SQLite and can restore chart state plus attached knowledge documents
- Chat now includes a lightweight safeguard layer for clearly unsafe sexual or violent misuse requests
- Request/error correlation uses `X-Request-ID`, with a stable JSON error envelope documented in [`docs/api/API_ERRORS.md`](docs/api/API_ERRORS.md)
- Liveness and readiness are split into `GET /api/health` and `GET /api/ready`
- Prometheus-style metrics are exposed at `GET /api/system/metrics`
- Idempotent retries are supported for `POST /api/upload/analyze` and chat session append requests (`POST /api/chat` with `session_id`)
- Shared-host operations now include documented graceful shutdown, rollback, backup/restore, and post-deploy checks
- RAG-0 is complete, and the first RAG-1/2 slice is live: `csv/xlsx` uploads now route through real ingestion/search/answer, `pdf/docx/md/txt` normalize into the same knowledge pipeline, and chat can use `knowledge_document_ids` for retrieval-backed generation instead of raw snippet dumps
- Generated non-executed chat files now download through persisted artifact ids under `/api/artifacts/{artifact_id}`
- Code sandbox execution is now a real gated capability: `POST /api/code-sandbox/exec` runs provider-backed shell work in `sync` or `async` mode, `GET /api/code-sandbox/executions/{execution_id}` and `/events` expose durable state/auditability, and `GET /api/code-sandbox/executions/{execution_id}/logs` streams replayable stdout/stderr over SSE. Docker is the default isolated backend; `localhost` is a trusted-dev fallback with weaker isolation.
- Workbench tasks now persist durable task rows, support polling and event timelines, and provide minimal execution for `plan`, `browse`, `deep_research`, and `canvas`; public-web retrieval is now an experimental bounded DDGS-backed evidence brief rather than a future-only placeholder
- **RAG-ready gate:** the product may be described as **RAG-ready** only when `python -m tools.quality.run_rag_eval` exits 0 (checked-in `evaldata/rag_eval_cases.jsonl`; see [evaldata/README.md](evaldata/README.md)) and retrieval quality notes in [docs/governance/PROJECT_STATUS.md](docs/governance/PROJECT_STATUS.md) stay aligned with that runner. CI runs the same command on every backend build.

## Quick Start

Development:

```bash
python3.14 -m venv .venv   # or any `python3` that matches CI (see `.github/workflows/ci.yml`)
source .venv/bin/activate
pip install -r requirements-ci.txt
cp .env.example .env
python3 -m uvicorn server:create_app --factory --host 0.0.0.0 --port 62606 --reload
```

Use **Python 3.14** for the venv when you can so `python -m tools.contracts.check_api_contract_sync` matches the CI backend job.

If you are on Windows and hit a Linux-targeted validation or packaging path, use the WSL guidance in [docs/operations/WSL_DEVELOPMENT.md](docs/operations/WSL_DEVELOPMENT.md).

Frontend dev server:

```bash
cd frontend
npm ci
npm run dev
```

Desktop shell scaffold (Phase 19A):

```bash
cd frontend
npm ci
npm run desktop:dev
```

Notes:

- the desktop shell now uses a **Tauri 2** scaffold under [frontend/src-tauri](/E:/simonbb/GOAT_AI/frontend/src-tauri)
- in dev mode it launches the existing FastAPI backend as a local child process and waits for `/api/health` before showing the main window

Packaged backend sidecar (Phase 19B):

```bash
pip install -r requirements-desktop-build.txt
python -m tools.desktop.build_desktop_sidecar
cd frontend
npm run desktop:build
```

Notes:

- `python -m tools.desktop.build_desktop_sidecar` freezes the backend entrypoint with **PyInstaller** and places the per-platform binary under [frontend/src-tauri/binaries](/E:/simonbb/GOAT_AI/frontend/src-tauri/binaries)
- `npm run desktop:build` now rebuilds the frozen sidecar before the Tauri packaging step
- packaged desktop builds launch the bundled backend sidecar locally and store SQLite/data files in the platform app-data directory instead of the repository root

Packaged desktop runtime configuration:

- Desktop builds inherit runtime configuration from the parent OS environment rather than a repo-local `.env`.
- Common knobs include `OLLAMA_BASE_URL`, `GOAT_FEATURE_CODE_SANDBOX`, `GOAT_CODE_SANDBOX_PROVIDER`, and `GOAT_DESKTOP_BACKEND_PORT`.
- Docker remains the default sandbox provider for packaged builds; `localhost` should be treated as a trusted development fallback, not a strong-isolation production path.

Windows desktop prerequisites can be bootstrapped with:

```powershell
.\scripts\desktop\install_desktop_prereqs.ps1 -Profile Dev
```

Profiles:

- `Runtime`: installs end-user runtimes for the packaged desktop app baseline (`WebView2`, plus `Ollama` by default)
- `Dev`: installs desktop build prerequisites (`Rustup`, `cargo` / `rustc`, Visual Studio Build Tools 2022 with the C++ workload) plus `WebView2`
- `All`: installs both runtime and development prerequisites

Production-style deploy:

```bash
bash ops/deploy/deploy.sh
```

Default deploys now use the standard Ollama address `http://127.0.0.1:11434` unless
`OLLAMA_BASE_URL` is explicitly set. The old sibling `ollama-local` / `11435` path is
no longer auto-detected or auto-started by the generic deploy chain.

Windows PowerShell:

```powershell
.\ops\deploy\deploy.ps1
```

Canonical checked-in operator assets live under `ops/deploy/`, `ops/systemd/`, and `ops/verification/`. Use those paths directly.

### Simon school Ubuntu server profile

The school-owned Ubuntu server keeps its `ollama-local` layout and helper scripts as an
explicit opt-in profile only.

- turn it on with `GOAT_USE_SCHOOL_OLLAMA_LOCAL=1` or `GOAT_OLLAMA_PROFILE=school-ubuntu`
- keep `OLLAMA_BASE_URL=http://127.0.0.1:11435` in the school server's `.env` or dedicated env file
- use [docs/operations/SCHOOL_UBUNTU_SERVER.md](docs/operations/SCHOOL_UBUNTU_SERVER.md) for the school-only runbook and service unit guidance

## Testing

Backend (canonical - matches CI):

```bash
python -m pytest __tests__/ -v --tb=short
```

Legacy optional runner for files still on `unittest` style:

```bash
python -m unittest discover -s __tests__ -p "test_*.py" -v
```

Targeted contract tests:

```bash
python -m pytest __tests__/contracts/test_api_blackbox_contract.py -v
```

Retrieval quality regression (RAG-3):

```bash
python -m tools.quality.run_rag_eval
```

Frontend:

```bash
cd frontend
npm run lint
npm run depcruise
npm run contract:check
npm test -- --run
npm run build
npm run bundle:check
```

## Parallel Development / Repository Governance

This repo uses four long-lived Codex owner lanes for parallel work:

- Lead/Platform
- Frontend
- Backend
- Docs/Assets

Default directory ownership lives in [`.github/CODEOWNERS`](.github/CODEOWNERS). Each owner thread should work primarily inside its owned paths and rebase from the latest `main`; `main` itself rebases `origin/main`. Shared-boundary changes such as API contracts, CI, and cross-layer tests should be explicitly coordinated by Lead/Platform.

Merges to `main` should be gated by GitHub branch protection, required checks, and code owner review. Lead/Platform gives the final merge recommendation after the relevant owner lanes review the change. Operational details for Codex threads live in [AGENTS.md](AGENTS.md), with repo-wide standards in [docs/standards/ENGINEERING_STANDARDS.md](docs/standards/ENGINEERING_STANDARDS.md).

P1 governance assets now live in-repo too:

- release workflow and approval policy: [docs/operations/RELEASE_GOVERNANCE.md](docs/operations/RELEASE_GOVERNANCE.md)
- security response / dependency refresh / credential rotation policy: [docs/governance/SECURITY_RESPONSE.md](docs/governance/SECURITY_RESPONSE.md)
- observability assets: [ops/observability/README.md](ops/observability/README.md)
- incident response starter runbook: [docs/operations/INCIDENT_TRIAGE.md](docs/operations/INCIDENT_TRIAGE.md)
- scheduled performance smoke: [`.github/workflows/performance-nightly.yml`](.github/workflows/performance-nightly.yml)
- scheduled quality + security evidence capture: [`.github/workflows/quality-trends.yml`](.github/workflows/quality-trends.yml)
- scheduled fault-injection drills: [`.github/workflows/fault-injection.yml`](.github/workflows/fault-injection.yml)
- desktop provenance + SBOM baseline: [`.github/workflows/desktop-provenance.yml`](.github/workflows/desktop-provenance.yml)

## Docs

- [AGENTS.md](AGENTS.md): short index for agents; **canonical rules:** [docs/standards/ENGINEERING_STANDARDS.md](docs/standards/ENGINEERING_STANDARDS.md)
- [docs/operations/WSL_DEVELOPMENT.md](docs/operations/WSL_DEVELOPMENT.md): selective WSL workflows for Linux-targeted validation on Windows
- [docs/decisions/README.md](docs/decisions/README.md): decision records, decision packages, and templates for architecture-sensitive changes
- [docs/governance/specs/README.md](docs/governance/specs/README.md): lightweight non-canonical `spec/plan/tasks` pilot for complex brownfield changes
- [docs/governance/PROJECT_STATUS.md](docs/governance/PROJECT_STATUS.md): current shipped state
- [docs/standards/APPEARANCE.md](docs/standards/APPEARANCE.md): appearance/theme architecture, controls, and extension rules
- [docs/api/API_REFERENCE.md](docs/api/API_REFERENCE.md): endpoint contract
- [docs/api/API_ERRORS.md](docs/api/API_ERRORS.md): stable error envelope and error-code rules
- [docs/operations/OPERATIONS.md](docs/operations/OPERATIONS.md): deploy, env vars, ops notes
- [docs/operations/VERCEL_FRONTEND_DEPLOY.md](docs/operations/VERCEL_FRONTEND_DEPLOY.md): Vercel frontend + `goat-api.duckdns.org` split-deploy runbook
- [docs/operations/SCHOOL_UBUNTU_SERVER.md](docs/operations/SCHOOL_UBUNTU_SERVER.md): school-only Ubuntu server profile for the `ollama-local` helper scripts and service unit
- [docs/operations/BACKUP_RESTORE.md](docs/operations/BACKUP_RESTORE.md): SQLite backup/restore drill
- [docs/operations/ROLLBACK.md](docs/operations/ROLLBACK.md): rollback procedure for shared-host deploys
- [docs/governance/SECURITY.md](docs/governance/SECURITY.md): upload/API threat notes and CI security posture
- [docs/governance/SECURITY_RESPONSE.md](docs/governance/SECURITY_RESPONSE.md): vulnerability response windows, dependency refresh cadence, and credential rotation policy
- [docs/governance/QUALITY_TRENDS.md](docs/governance/QUALITY_TRENDS.md): recurring quality snapshot workflow and current trend baseline
- [docs/operations/RELEASE_GOVERNANCE.md](docs/operations/RELEASE_GOVERNANCE.md): staged release and production approval policy
- [docs/operations/INCIDENT_TRIAGE.md](docs/operations/INCIDENT_TRIAGE.md): first-response runbook for readiness, latency, retrieval, and feature-gate failures
- [docs/governance/ROADMAP.md](docs/governance/ROADMAP.md): unfinished backlog and priority queue
- [docs/governance/ROADMAP_ARCHIVE.md](docs/governance/ROADMAP_ARCHIVE.md): historical roadmap content and phase closeouts
- [docs/standards/ENGINEERING_STANDARDS.md](docs/standards/ENGINEERING_STANDARDS.md): coding and process standards (single source of truth)
- [ops/observability/README.md](ops/observability/README.md): versioned scrape config, alert rules, and dashboards
- [`examples/`](examples): demo/example assets kept out of canonical docs

Capacity/load validation:

```bash
python -m tools.quality.load_chat_smoke --base-url http://127.0.0.1:62606 --model gemma4:26b --runs 20 --show-system-inference
```
