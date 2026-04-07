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

## Quick Start

Development:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 -m uvicorn server:app --host 0.0.0.0 --port 8002 --reload
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
- [docs/OPERATIONS.md](docs/OPERATIONS.md): deploy, env vars, ops notes
- [docs/ROADMAP.md](docs/ROADMAP.md): shipped phases and refactor roadmap
- [docs/ENGINEERING_STANDARDS.md](docs/ENGINEERING_STANDARDS.md): coding standards
