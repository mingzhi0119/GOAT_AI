# GOAT AI Agent Memory

This file is the durable repo memory for future coding agents working in this project.
It summarizes the operating rules in `.cursor/rules/` so the repo can be recovered even if editor-specific rules are lost.

## Purpose

- Preserve the engineering standards and server constraints for GOAT AI.
- Keep future changes aligned with the current architecture.
- Avoid repeating past deployment mistakes on the live server.
- Prefer stable contracts over re-discovering implementation details on every task.

## Core Project Direction

- This project must stay engineering-grade.
- Prioritize interfacization: define clear interfaces between layers, inject dependencies through typed boundaries, and avoid tightly coupled feature code.
- Favor maintainable structure over fast patchwork. If a change works but weakens boundaries, refactor it before calling it done.

## API Working Rule

- Treat the API surface as a black-box contract first, not a source-reading exercise.
- For existing APIs, prefer these artifacts before opening implementation files:
  - `__tests__/test_api_blackbox_contract.py`
  - `__tests__/test_api_auth.py`
  - `__tests__/test_api_security.py`
  - `docs/openapi.json`
  - `docs/api.llm.yaml`
- Only inspect API implementation when:
  - changing the API behavior
  - contract tests/docs disagree with runtime behavior
  - debugging requires details not visible from the contract layer
- Goal: save tokens, reduce duplicate analysis, and rely on stable interface contracts.

## Project Snapshot

- Repo: `GOAT_AI`
- Main deploy target: Ubuntu A100 shared host
- App shape: FastAPI backend serving a React SPA
- Production port: `62606`
- Frontend build tool: Vite
- Frontend runtime target: Node 24 on server/CI
- Backend runtime target: Python 3.12

## Five Non-Negotiables

1. Fail fast, fail loud. Invalid config must crash at startup with a clear message.
2. Decouple by boundary. HTTP handler -> service -> client. No business logic in route handlers.
3. Portable by default. Code must work on Windows dev and Ubuntu prod without edits.
4. Type everything. Untyped functions are not acceptable.
5. Test the boundary, mock the world. Unit tests own logic; integration tests are narrow.

## Cross-Environment Rules

- Use `pathlib.Path` for paths. Do not hardcode platform-specific path strings.
- Use env vars for ports, URLs, and secrets. Do not hardcode them in source.
- Always use `encoding="utf-8"` for file reads/writes.
- Keep `.env` out of git. Commit `.env.example` instead.
- Keep exact dependency locks: `requirements.txt` pinned, `package-lock.json` committed, and use `npm ci` in CI/deploy.
- Validate config at startup, never lazily inside request handling.

## Production Server Constraints

These constraints are important and easy to forget.

- The production host is a shared JupyterHub-style environment.
- No `sudo` / no root. Do not assume `apt`, system-wide `systemctl`, nginx reloads, or `/etc/*` access.
- `systemctl --user` may work, but may also fail in SSH sessions. Always preserve the `nohup` + `logs/fastapi.pid` fallback path.
- Uvicorn on `0.0.0.0:62606` is valid for this user.
- GPU note: prefer `GOAT_GPU_UUID=GPU-fb2cf8f7-e9bf-f136-a3bb-e150426598e8` for the A100. Do not default to the GT 1030.

## Deploy Rules

- This repo is now developed directly on the server.
- `deploy.sh` must not assume a `git pull` or `git reset --hard` by default.
- Deploy from the current local checkout unless explicit sync is requested.
- Keep `SYNC_GIT=1` as an explicit opt-in only.
- Keep `nohup` fallback deployment behavior intact.
- Runtime target selection is interface-driven: `GOAT_DEPLOY_TARGET=auto` must prefer `GOAT_SERVER_PORT` (default `62606`) and fall back to `GOAT_LOCAL_PORT` (default `8002`) only when the current environment cannot bind/use the server port.
- The deploy/ops contract for target resolution is exposed at `GET /api/system/runtime-target`; keep script behavior and API output aligned.

## Python Backend Standards

- Add `from __future__ import annotations` at the top of every Python file.
- Fully annotate every function and method, including return types.
- Use `Protocol` for injectable dependencies when appropriate.
- Structured data must use `BaseModel` or `dataclass`, not loose dicts across boundaries.
- Never read `os.environ` inside request handlers.
- Use layered error handling: services/clients raise domain exceptions, route handlers translate them to sanitized `HTTPException`, and startup config errors stop the app immediately.
- Use `logging.getLogger(__name__)`, never `print()`.
- Do not log secrets, full uploads, or raw user prompts at INFO+.

## Backend Architecture Rules

- `backend/routers/`: validate input, call services, return response
- `backend/services/`: business logic
- `backend/models/`: Pydantic schemas only
- `goat_ai/`: shared code, no FastAPI imports
- `backend/main.py`: app factory and startup wiring

Do not move business logic into route handlers.

## React / TypeScript Standards

- TypeScript must stay strict:
  - `strict: true`
  - `noUncheckedIndexedAccess: true`
  - `noImplicitReturns: true`
- No `any`
- No `@ts-ignore`
- All network calls belong in `frontend/src/api/*.ts`
- Components render UI; hooks own client-side behavior/state
- Hooks return typed objects, not wide positional tuples
- Hooks must not import from `src/components/`
- Use an error boundary around async-heavy UI sections

## Frontend Architecture Rules

- `frontend/src/api/`: fetch wrappers and shared API types
- `frontend/src/hooks/`: stateful client logic
- `frontend/src/components/`: rendering
- SSE remains the streaming mechanism; do not replace with WebSocket without a deliberate design change
- Chart rendering is now Apache ECharts-based. Keep the backend contract constrained: models emit `ChartIntentV2` through native tool calling, and backend services compile that intent into `ChartSpecV2` / ECharts `option`. Do not let models emit raw chart-library config directly.
- If the selected Ollama model does not report native tool support, chart rendering must stay disabled rather than falling back to pseudo chart markup.

## Theme Rules

- Light/dark mode uses a `.dark` class on `<html>`
- Theme state persists in `localStorage`
- Global theme tokens live in `frontend/src/styles/global.css`

## Testing Standards

### Python

- Test files live in `__tests__/`
- Mock at the protocol boundary; do not hit real Ollama in unit tests
- Prefer fixtures/shared setup instead of global mutable state
- Cover happy path plus edge cases
- Do not use `time.sleep()` in tests
- Common commands in this repo include `python -m unittest discover -s __tests__ -p "test_*.py" -v` and targeted `python -m pytest ...`; preserve the same isolation and mocking discipline regardless of runner.

### TypeScript

- Use Vitest and React Testing Library
- Mock `fetch`, never hit the live backend
- Assert behavior and user-visible output, not CSS implementation details

## Documentation Update Rules

Update docs when behavior changes:

- `README.md` for architecture, structure, or developer workflow changes
- `docs/openapi.json` for the committed OpenAPI contract generated from FastAPI
- `docs/api.llm.yaml` for the committed LLM-optimized compact API contract
- `docs/API_REFERENCE.md` for human-readable endpoint reference
- `docs/OPERATIONS.md` for env vars, deploy, startup, or host operations changes
- `docs/PROJECT_STATUS.md` for current shipped state
- `docs/ROADMAP.md` for phase completion and future work

## API Contract Memory

- The canonical machine-readable API contract is `docs/openapi.json`.
- It must stay in OpenAPI `3.2.0` format and reflect the current FastAPI app.
- Regenerate it from `backend.main:app` after endpoint/schema changes so the committed spec and runtime `/openapi.json` do not drift.
- The canonical compact LLM-facing API file is `docs/api.llm.yaml`.
- Regenerate `docs/api.llm.yaml` from `docs/openapi.json` with `python tools/generate_llm_api_yaml.py`; do not hand-maintain it unless you are also updating the generator.
- The canonical executable API contract is the black-box suite in `__tests__/test_api_blackbox_contract.py`; keep it aligned with auth/security suites and use it as the first reference for API behavior.

## Commit Hygiene

Before committing:

- No `print()`
- No commented-out code
- No hardcoded secrets/ports/paths
- New functions are typed
- New logic has tests where practical
- Dependency files are updated if dependencies changed
- Docs are updated when user-facing or ops behavior changes

## Recovery Notes

- If local work appears lost, check `git reflog` before assuming it is gone.
- Be careful with `git reset --hard` on this server because development happens directly on the host.
- Avoid committing `.venv/`, PID files, SQLite runtime files, notebook checkpoints, or other machine-local artifacts.

## Source Rules

This memory file was derived from `.cursor/rules/` and should stay shorter than the combined editor-specific rules.
