# GOAT AI

Strategic Intelligence assistant for Simon Business School, University of Rochester.

- Example public deployment: <https://ai.simonbb.com/mingzhi/> (not the only environment the app can run in)
- Repo: <https://github.com/mingzhi0119/GOAT_AI>
- Current snapshot: [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md)
- API contract: [docs/API_REFERENCE.md](docs/API_REFERENCE.md)

## Environments

- **Portable by design:** the same repo is meant to run on **Windows, macOS, and Linux** for development, and on **various Linux (or container) server layouts** for production—not tied to a single school-owned Ubuntu image. Paths, ports, GPU selection, and secrets are **environment-driven** (see `.env.example` and [docs/OPERATIONS.md](docs/OPERATIONS.md)); avoid hardcoding host-specific assumptions in code.
- **Reference vs local:** a documented production URL in [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) is a **reference deployment**, not a constraint on where you may install or develop.

### Capability-based / high-risk features

Some capabilities (for example a future **model-driven code execution sandbox**) require **strong isolation** (typically **Docker** or an equivalent approved container runtime). Separate concerns:

| Concern | What it answers | Typical outcome when blocked |
|--------|-----------------|------------------------------|
| **Authorization / policy** | Is *this caller* (user, role, tenant, API key scope) allowed? | **403** + stable `code` (e.g. `FEATURE_DISABLED`) |
| **Capability / runtime** | Is *this deployment* configured and are dependencies (Docker socket, etc.) ready? | **503** + stable `code` (e.g. `FEATURE_UNAVAILABLE`) |

| Host situation | Expected behavior |
|----------------|-------------------|
| Docker (or approved runtime) available and operators enable the feature | Code-execution sandbox **may** be turned on after configuration and review ([docs/OPERATIONS.md](docs/OPERATIONS.md)). |
| No Docker / no isolation / operator opts out | **Disable** code execution; the rest of the app (chat, RAG, uploads, downloads of **non-executed** generated files) continues to work within normal limits. |

Until such a feature ships, this table documents the **intended** model: **high-risk operations are gated by explicit configuration and runtime readiness**, not on by default; **per-caller policy** is documented separately in the AuthZ roadmap.

**Industrial implementation pattern** (config + probe + API + service enforcement + tests): see [docs/ENGINEERING_STANDARDS.md](docs/ENGINEERING_STANDARDS.md) **§15 Feature enable/disable and gating**.

## Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, Uvicorn, Python 3.12 |
| Frontend | React 19, TypeScript, Vite 8 |
| LLM runtime | Ollama |
| Data parsing | pandas, openpyxl, python-docx, pypdf |
| Persistence | SQLite |
| Charts | Apache ECharts |

## Architecture

Typical production path: **browser → reverse proxy (e.g. nginx) → FastAPI/Uvicorn** on a configured port (default **62606** via `GOAT_SERVER_PORT` / runtime target; see [docs/OPERATIONS.md](docs/OPERATIONS.md)). Local development often uses the same app process without nginx.

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
- `GET /api/history`
- `GET /api/history/{session_id}`
- `DELETE /api/history`
- `DELETE /api/history/{session_id}`
- `GET /api/system/gpu`
- `GET /api/system/inference`
- `GET /api/system/runtime-target`
- `GET /api/system/features` (capability-gated features: config + host probe)
- `POST /api/code-sandbox/exec` (scaffold; 403 when disabled, 501 when enabled but not implemented)

## Current behavior

- Chat streams typed SSE event objects: `token`, `chart_spec`, `error`, `done`
- Upload SSE ingests supported files into the knowledge pipeline and emits `knowledge_ready`, `error`, `done`
- Charts are created only from native Ollama tool calls during chat
- Session history is persisted in SQLite and can restore chart state plus attached knowledge documents
- Chat now includes a lightweight safeguard layer for clearly unsafe sexual or violent misuse requests
- Request/error correlation uses `X-Request-ID`, with a stable JSON error envelope documented in [`docs/API_ERRORS.md`](docs/API_ERRORS.md)
- Liveness and readiness are split into `GET /api/health` and `GET /api/ready`
- Prometheus-style metrics are exposed at `GET /api/system/metrics`
- Idempotent retries are supported for `POST /api/upload/analyze` and chat session append requests (`POST /api/chat` with `session_id`)
- Shared-host operations now include documented graceful shutdown, rollback, backup/restore, and post-deploy checks
- RAG-0 is complete, and the first RAG-1/2 slice is live: `csv/xlsx` uploads now route through real ingestion/search/answer, `pdf/docx/md/txt` normalize into the same knowledge pipeline, and chat can use `knowledge_document_ids` for retrieval-backed replies
- **RAG-ready gate:** the product may be described as **RAG-ready** only when `python tools/run_rag_eval.py` exits 0 (checked-in `evaldata/rag_eval_cases.jsonl`) and retrieval quality notes in [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) stay aligned with that runner

## Quick Start

Development:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 -m uvicorn server:app --host 0.0.0.0 --port 62606 --reload
```

Frontend dev server:

```bash
cd frontend
npm ci
npm run dev
```

Production-style deploy:

```bash
bash deploy.sh
```

Windows PowerShell:

```powershell
.\deploy.ps1
```

## Testing

Backend:

```bash
python -m unittest discover -s __tests__ -p "test_*.py" -v
```

Targeted contract tests:

```bash
python -m pytest __tests__/test_api_blackbox_contract.py -v
```

Retrieval quality regression (RAG-3):

```bash
python tools/run_rag_eval.py
```

Frontend:

```bash
cd frontend
npm test -- --run
npm run build
```

## Docs

- [AGENTS.md](AGENTS.md): short index for agents; **canonical rules:** [docs/ENGINEERING_STANDARDS.md](docs/ENGINEERING_STANDARDS.md)
- [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md): current shipped state
- [docs/API_REFERENCE.md](docs/API_REFERENCE.md): endpoint contract
- [docs/API_ERRORS.md](docs/API_ERRORS.md): stable error envelope and error-code rules
- [docs/OPERATIONS.md](docs/OPERATIONS.md): deploy, env vars, ops notes
- [docs/BACKUP_RESTORE.md](docs/BACKUP_RESTORE.md): SQLite backup/restore drill
- [docs/ROLLBACK.md](docs/ROLLBACK.md): rollback procedure for shared-host deploys
- [docs/SECURITY.md](docs/SECURITY.md): upload/API threat notes and CI security posture
- [docs/ROADMAP.md](docs/ROADMAP.md): shipped phases and refactor roadmap
- [docs/ENGINEERING_STANDARDS.md](docs/ENGINEERING_STANDARDS.md): coding and process standards (single source of truth)

Capacity/load validation:

```bash
python tools/load_chat_smoke.py --base-url http://127.0.0.1:62606 --model gemma4:26b --runs 20 --show-system-inference
```
