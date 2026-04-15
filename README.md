# GOAT AI

Strategic Intelligence assistant for Simon Business School, University of
Rochester.

- Example public deployment: <https://goat-dev.vercel.app>
- Public backend: <https://goat-api.duckdns.org>
- Repo: <https://github.com/mingzhi0119/GOAT_AI>
- Shipped status: [docs/governance/PROJECT_STATUS.md](docs/governance/PROJECT_STATUS.md)
- Active unfinished work: [docs/governance/ROADMAP.md](docs/governance/ROADMAP.md)

## Overview

GOAT AI is a React + FastAPI application with an Ollama-backed local/hosted AI
runtime, persisted sessions and artifacts, upload/knowledge flows, and a small
set of deployment shapes:

- `GOAT_DEPLOY_MODE=0`: local
- `GOAT_DEPLOY_MODE=1`: school server
- `GOAT_DEPLOY_MODE=2`: remote

Detailed behavior, contracts, architecture, and operational truth now live in
`docs/`. This README is intentionally kept as a compact entrypoint.

## Quick Start

Backend dev:

```bash
python3.14 -m venv .venv
source .venv/bin/activate
pip install -r requirements-ci.txt
cp .env.example .env
python3 -m uvicorn server:create_app --factory --host 0.0.0.0 --port 62606 --reload
```

Frontend dev:

```bash
cd frontend
npm ci
npm run dev
```

## Build Entrypoints

Local Linux build:

```bash
bash ops/build/build_local.sh
```

Local Windows build:

```powershell
.\ops\build\build_local.ps1
```

School server build:

```bash
bash ops/build/build_school_server.sh
```

## Deploy Entrypoints

Local Linux deploy:

```bash
bash ops/deploy/deploy.sh
```

Local Windows deploy:

```powershell
.\ops\deploy\deploy.ps1
```

School server deploy:

```bash
bash ops/deploy/deploy_school_server.sh
```

Remote backend deploy:

```bash
bash ops/deploy/deploy_remote_server.sh
```

## Testing

Backend:

```bash
python -m pytest __tests__/ -v --tb=short
```

Frontend:

```bash
cd frontend
npm run lint
npm run depcruise
npm run contract:check
npm test -- --run
npm run build
```

## Docs

- [AGENTS.md](AGENTS.md)
- [docs/standards/ENGINEERING_STANDARDS.md](docs/standards/ENGINEERING_STANDARDS.md)
- [docs/api/API_REFERENCE.md](docs/api/API_REFERENCE.md)
- [docs/api/API_ERRORS.md](docs/api/API_ERRORS.md)
- [docs/operations/OPERATIONS.md](docs/operations/OPERATIONS.md)
- [docs/operations/VERCEL_FRONTEND_DEPLOY.md](docs/operations/VERCEL_FRONTEND_DEPLOY.md)
- [docs/operations/SCHOOL_UBUNTU_SERVER.md](docs/operations/SCHOOL_UBUNTU_SERVER.md)
- [docs/operations/WSL_DEVELOPMENT.md](docs/operations/WSL_DEVELOPMENT.md)
- [docs/governance/PROJECT_STATUS.md](docs/governance/PROJECT_STATUS.md)
- [docs/governance/ROADMAP.md](docs/governance/ROADMAP.md)
- [docs/decisions/README.md](docs/decisions/README.md)
