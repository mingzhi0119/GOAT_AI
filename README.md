# GOAT AI

Strategic Intelligence assistant for Simon Business School, University of Rochester.

- Public URL: <https://ai.simonbb.com/mingzhi/>
- Repo: <https://github.com/mingzhi0119/GOAT_AI>
- Current snapshot: [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md)
- API contract: [docs/API_REFERENCE.md](docs/API_REFERENCE.md)

## Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, Uvicorn, Python 3.12 |
| Frontend | React 19, TypeScript, Vite 8 |
| LLM runtime | Ollama |
| Data parsing | pandas, openpyxl |
| Persistence | SQLite |
| Charts | Apache ECharts |

## Architecture

Browser -> nginx -> FastAPI/Uvicorn on `:62606`

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
- `GET /api/history`
- `GET /api/history/{session_id}`
- `DELETE /api/history`
- `DELETE /api/history/{session_id}`
- `GET /api/system/gpu`
- `GET /api/system/inference`
- `GET /api/system/runtime-target`

## Current behavior

- Chat streams typed SSE event objects: `token`, `chart_spec`, `error`, `done`
- Upload SSE emits `file_context` and `done`
- Charts are created only from native Ollama tool calls during chat
- Session history is persisted in SQLite and can restore chart/file-context state
- Chat now includes a lightweight safeguard layer for clearly unsafe sexual or violent misuse requests
- Request/error correlation uses `X-Request-ID`, with a stable JSON error envelope documented in [`docs/API_ERRORS.md`](docs/API_ERRORS.md)
- Liveness and readiness are split into `GET /api/health` and `GET /api/ready`
- Prometheus-style metrics are exposed at `GET /api/system/metrics`
- Idempotent retries are supported for `POST /api/upload/analyze` and chat session append requests (`POST /api/chat` with `session_id`)
- Shared-host operations now include documented graceful shutdown, rollback, backup/restore, and post-deploy checks

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

Frontend:

```bash
cd frontend
npm test -- --run
npm run build
```

## Docs

- [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md): current shipped state
- [docs/API_REFERENCE.md](docs/API_REFERENCE.md): endpoint contract
- [docs/API_ERRORS.md](docs/API_ERRORS.md): stable error envelope and error-code rules
- [docs/OPERATIONS.md](docs/OPERATIONS.md): deploy, env vars, ops notes
- [docs/BACKUP_RESTORE.md](docs/BACKUP_RESTORE.md): SQLite backup/restore drill
- [docs/ROLLBACK.md](docs/ROLLBACK.md): rollback procedure for shared-host deploys
- [docs/SECURITY.md](docs/SECURITY.md): upload/API threat notes and CI security posture
- [docs/ROADMAP.md](docs/ROADMAP.md): shipped phases and refactor roadmap
- [docs/ENGINEERING_STANDARDS.md](docs/ENGINEERING_STANDARDS.md): coding standards

Capacity/load validation:

```bash
python tools/load_chat_smoke.py --base-url http://127.0.0.1:62606 --model gemma4:26b --runs 20 --show-system-inference
```
