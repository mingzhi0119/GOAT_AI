# GOAT AI 鈥?Claude Code Guide

Strategic Intelligence assistant for Simon Business School, University of Rochester.
Backend: FastAPI + Python 3.14 路 Frontend: React 19 + TypeScript + Vite 8 路 LLM: Ollama 路 DB: SQLite 路 Port: 62606

Canonical rules live in [`docs/standards/ENGINEERING_STANDARDS.md`](docs/standards/ENGINEERING_STANDARDS.md). This file is a durable working reference 鈥?keep it aligned with ENGINEERING_STANDARDS, not a replacement for it.

---

## Five non-negotiables

1. **Fail fast, fail loud** 鈥?bad config or missing env vars crash at startup with a clear message; never fail silently at runtime.
2. **Decouple by boundary** 鈥?handler 鈫?application 鈫?service 鈫?domain. No business logic in route handlers. No I/O inside domain models.
3. **Portable by default** 鈥?identical behavior on Windows dev and Linux prod without source edits. No hardcoded paths, ports, or host names.
4. **Type everything** 鈥?every function signature carries types; use `Protocol` for injectable dependencies, `dataclass` / `BaseModel` for structured data.
5. **Test the boundary, mock the world** 鈥?unit tests own pure logic; integration tests own real I/O at Protocol boundaries; nothing else hits the network.

---

## Layer architecture (enforced by import-linter)

```
backend/routers/          鈫?validate input, call application, return response 鈥?nothing else
backend/application/      鈫?use-case orchestration; owns ports, stable exceptions
backend/services/         鈫?stateless business logic, no HTTP primitives
backend/domain/           鈫?policies and invariants (SafeguardPolicy, ChartProvenancePolicy)
backend/models/           鈫?Pydantic shapes only, no methods beyond validators
goat_ai/                  鈫?innermost shared lib (LLM client, uploads, tools); never imports backend
```

**Direction:** `routers 鈫?application 鈫?services 鈫?domain 鈫?models 鈫?goat_ai`

Run `lint-imports` (configured in `pyproject.toml`) before pytest 鈥?CI does the same. Before every merge or hand-off, run the full **CI parity** block under [Testing](#testing) so local results match `.github/workflows/ci.yml`.

Key contract face: `backend.application.ports` exports `Settings`, `LLMClient`, `SessionRepository`, `ConversationLogger`, `TitleGenerator`, `SafeguardService`, `TabularContextExtractor`, and stable shared exceptions. Routers and application modules import from here, not from `backend.services.*` directly.

Details: [`docs/architecture/DEPENDENCY_GRAPH.md`](docs/architecture/DEPENDENCY_GRAPH.md) 路 [`docs/architecture/PORTS.md`](docs/architecture/PORTS.md)

---

## Running the project

```bash
# Backend (development)
python3.14 -m venv .venv && source .venv/bin/activate
pip install -r requirements-ci.txt
cp .env.example .env
python3 -m uvicorn server:create_app --factory --host 0.0.0.0 --port 62606 --reload

# Frontend (development)
cd frontend && npm ci && npm run dev

# Production deploy
bash ops/deploy/deploy.sh          # Linux
.\ops\deploy\deploy.ps1            # Windows PowerShell
```

---

## Testing

### CI parity (run before every code delivery)

These commands mirror the `backend` and `frontend` jobs in [`.github/workflows/ci.yml`](.github/workflows/ci.yml). Use **Python 3.14** and `pip install -r requirements-ci.txt` (or equivalent) so `lint-imports`, `tools.contracts.check_api_contract_sync`, and OpenAPI artifacts stay aligned with CI.

**Backend (repository root):**

```bash
ruff check backend goat_ai scripts tools __tests__
ruff format --check backend goat_ai scripts tools __tests__
pip-audit -r requirements-ci.txt
lint-imports
python -m tools.quality.run_rag_eval
python -m tools.contracts.check_api_contract_sync
python -m pytest __tests__/ -v --tb=short
```

**Frontend** (when `frontend/` changed; Node **24.14.x** per workflow):

```bash
cd frontend && npm ci && npm test -- --run && npm run build
```

### Focused runs

```bash
# Canonical pytest (subset of CI parity)
python -m pytest __tests__/ -v --tb=short

# Integration tier only (requires no live Ollama)
python -m pytest __tests__/integration/ -v -m integration

# Targeted contract tests
python -m pytest __tests__/contracts/test_api_blackbox_contract.py -v

# RAG eval gate (must stay green)
python -m tools.quality.run_rag_eval

# Frontend tests + build only (if deps already installed)
cd frontend && npm test -- --run && npm run build
```

Never `time.sleep` in tests to wait for TTL 鈥?use `FakeClock` from `goat_ai/clocks.py`.
Mock Ollama at the `LLMClient` Protocol boundary; never hit a live Ollama in unit tests.

---

## Developer CLI (`tools/`)

Run from the repo root 鈥?`tools/` is a package, no `PYTHONPATH` tricks needed.

| Command | Purpose |
|---------|---------|
| `python -m tools.quality.run_rag_eval` | RAG quality gate (CI runs this on every backend build) |
| `python -m tools.contracts.check_api_contract_sync` | Verify `docs/api/openapi.json` matches the live FastAPI app |
| `python -m tools.contracts.generate_llm_api_yaml` | Regenerate `docs/api/api.llm.yaml` |
| `python -m tools.contracts.regenerate_openapi_json` | Regenerate `docs/api/openapi.json` (use Python 3.14 to match CI) |
| `python -m tools.quality.load_chat_smoke --base-url http://127.0.0.1:62606 --model <model>` | p50/p95 load smoke |

---

## Where to look first

| Task | Start here |
|------|-----------|
| API behavior / endpoint contracts | `__tests__/contracts/test_api_blackbox_contract.py`, `docs/api/openapi.json`, `docs/api/api.llm.yaml` |
| Auth / security rules | `__tests__/contracts/test_api_authz.py`, `docs/governance/SECURITY.md` |
| Domain terms (session, turn, chart, safeguard) | [`docs/architecture/DOMAIN.md`](docs/architecture/DOMAIN.md) |
| Layer import rules | [`docs/architecture/DEPENDENCY_GRAPH.md`](docs/architecture/DEPENDENCY_GRAPH.md), `pyproject.toml` `[tool.importlinter]` |
| Session JSON shape / versioning | [`docs/architecture/SESSION_SCHEMA.md`](docs/architecture/SESSION_SCHEMA.md) |
| Injectable ports (Protocols) | [`docs/architecture/PORTS.md`](docs/architecture/PORTS.md) |
| Env vars, deploy, ops | [`docs/operations/OPERATIONS.md`](docs/operations/OPERATIONS.md) |
| Current shipped state | [`docs/governance/PROJECT_STATUS.md`](docs/governance/PROJECT_STATUS.md) |
| Phase history and next work | [`docs/governance/ROADMAP.md`](docs/governance/ROADMAP.md) |
| Error codes / envelope | [`docs/api/API_ERRORS.md`](docs/api/API_ERRORS.md) |

---

## Current phase status

All work through **Phase 15.11** is complete on `main`.

Phase 16 items (code sandbox, Postgres, multi-tenant AuthN) each require a Decision Log entry before implementation.

---

## Documentation rules

- `docs/` and `README.md` are **English-only**. No non-English prose in committed files.
- Keep docs UTF-8 without BOM. Root `.editorconfig` must declare `charset = utf-8`.
- When behavior changes, update **all** relevant artifacts in the same PR:

| Changed | Update |
|---------|--------|
| HTTP endpoints or schemas | `docs/api/openapi.json`, `docs/api/api.llm.yaml`, `docs/api/API_REFERENCE.md` |
| Domain terms, chart/safeguard/session semantics | `docs/architecture/DOMAIN.md` |
| Session JSON shape or `SESSION_PAYLOAD_VERSION` | `docs/architecture/SESSION_SCHEMA.md` |
| Injectable ports or import-layer rules | `docs/architecture/PORTS.md`, `docs/architecture/DEPENDENCY_GRAPH.md` |
| New env var or startup step | `docs/operations/OPERATIONS.md`, `.env.example` |
| Current shipped state | `docs/governance/PROJECT_STATUS.md` |
| Phase completion or new planned work | `docs/governance/ROADMAP.md` |
| RAG retrieval / rerank / eval cases | `evaldata/README.md`, `evaldata/VERSION` |

---

## Feature gating (high-risk capabilities)

Two distinct gates 鈥?do not conflate them:

| Gate | HTTP | Code | When |
|------|------|------|------|
| **Policy / AuthZ** | 403 | `FEATURE_DISABLED` | Caller not permitted |
| **Runtime / capability** | 503 | `FEATURE_UNAVAILABLE` | Deployment not configured or dependency missing |

Enforcement is **layered** (config 鈫?startup probe 鈫?service 鈫?route 鈫?frontend). Frontend is UX only, not a security boundary. Full pattern: [ENGINEERING_STANDARDS.md](docs/standards/ENGINEERING_STANDARDS.md) Section 15.

---

## Key invariants to preserve

- **Chart specs** stored on a session must include a `version` field (invariant in `build_session_payload`).
- **Session messages** are dual-read/write: new `session_messages` table + legacy JSON blob. Do not break the compatibility codec.
- **`log_service` imports** are allowed only in `backend/services/log_service.py` and `backend/services/chat_runtime.py` 鈥?enforced by `__tests__/governance/test_architecture_boundaries.py`.
- **Routers** must not import `goat_ai` directly or use `httpx` / `requests` / `pandas` / `openpyxl` 鈥?enforced by `__tests__/governance/test_router_direct_imports.py`.
- **RAG eval gate** (`python -m tools.quality.run_rag_eval`) must stay green; do not describe the system as "RAG-ready" unless it passes.

---

## Ops constraints (shared host)

- No root, no system nginx reloads, `systemctl --user` may be unavailable.
- **`nohup` + `var/logs/fastapi.pid`** is the permanent fallback for process management.
- Preferred GPU: A100 via `GOAT_GPU_UUID`.
- `deploy.sh` deploys the current checkout by default; `SYNC_GIT=1` to pull first.
- Backup/restore runbook: [`docs/operations/BACKUP_RESTORE.md`](docs/operations/BACKUP_RESTORE.md) 路 Rollback: [`docs/operations/ROLLBACK.md`](docs/operations/ROLLBACK.md)
