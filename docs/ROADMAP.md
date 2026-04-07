# GOAT AI Roadmap

> Last updated: 2026-04-07
> Current release: **v1.2.0**
> Compact snapshot: [PROJECT_STATUS.md](PROJECT_STATUS.md)

---

## Shipped (v1.2.0)

| Phase | Content |
|-------|---------|
| 0 | Environment verification: Node 24, Vite 8, FastAPI smoke test |
| 1 | FastAPI backend: `/api/health`, `/api/models`, `/api/chat` SSE, `/api/upload` SSE |
| 2 | React frontend: Sidebar, ChatWindow, MessageBubble, FileUpload, `useChat`/`useModels`/`useTheme`, Tailwind branding |
| 3 | Production deploy: `deploy.sh` local-checkout flow, Uvicorn on `:62606`, nginx proxy path |
| 4 | Product polish: copy button, error boundary, refined branding assets, layout cleanup |
| 5 | Reliability and UX: stop streaming, local session restore, SQLite conversation logging |
| 6 | Core feature expansion: conversation history sidebar, file-context persistence across turns |
| 7 | Quality and observability hardening: user-space log rotation, no-root deploy fallback, backend tests, frontend Vitest, CI, request IDs, latency metrics |
| 8 | Charting and telemetry: structured `chart_spec`, Apache ECharts `ChartCard`, real A100 GPU telemetry, rolling inference latency, Markdown export, dependency-safe frontend deploys |
| 9 | Access and security: API key protection, rate limiting, request tracing headers, production-safe access controls |
| 10 | Native chart-tool path: constrained `ChartIntentV2` -> `ChartSpecV2` compiler, Ollama tool-capability checks, tool-call-only chart rendering |

---

## Phase 11: Industrialization and Decoupling

Status legend:
- `[ ]` Not started
- `[~]` In progress
- `[x]` Completed

Objective:
- Bring the codebase in line with the engineering contract in `AGENTS.md`: industrial-grade boundaries, typed interfaces, and maintainable service decomposition.
- Reduce coupling between transport, orchestration, persistence, and UI state so features can evolve without repeatedly editing the same large files.

Execution plan:

1. `[~]` Split backend chat orchestration into focused services
   - Extract `PromptComposer`, `ChartToolOrchestrator`, `ChatStreamService`, and `SessionPersistenceService` from the current chat flow.
   - Keep routers thin: input validation, dependency wiring, and HTTP translation only.
   - Remove the current "god service" pattern where prompt logic, chart logic, SSE formatting, logging, and session writes live together.

2. `[~]` Replace direct infrastructure calls with injected interfaces
   - Introduce typed Protocol/repository boundaries for session storage, conversation logging, title generation, and tabular-context extraction.
   - Remove direct `requests` calls and static persistence helpers from business services.
   - Make unit tests target service interfaces instead of concrete HTTP or SQLite behavior.

3. `[~]` Replace magic-string protocols with typed domain payloads
   - Stop using raw text markers such as `CHART_DATA_CSV`, hidden acknowledgement messages, and `__chart__` sentinels as the primary application contract.
   - Introduce explicit models for file context, stored chart state, and stream payloads.
   - Keep compatibility shims isolated at the edges while migrating old sessions safely.

4. `[x]` Formalize the SSE event contract
   - Standardize stream frames as typed event objects such as `token`, `chart_spec`, `done`, and `error`.
   - Remove mixed string/object sentinel parsing from frontend clients.
   - Regenerate OpenAPI and compact LLM-facing API contracts after the stream protocol is stabilized.

5. `[x]` Introduce a frontend chat-session controller
   - Move session restore, chart restore, file-context injection, and send-policy logic out of `App.tsx` and transport hooks into a dedicated `useChatSession` store/controller.
   - Keep components focused on rendering and user interaction.
   - Make session hydration rules explicit instead of encoding them indirectly in hidden-message behavior.

6. `[x]` Consolidate upload handling behind a shared boundary
   - Remove duplicated upload filename/extension/read logic across routes.
   - Introduce a single typed upload parsing/application service used by both SSE and JSON endpoints.
   - Keep route handlers free of repeated file validation and branching.

7. `[~]` Add architecture tests and documentation gates
   - Add tests that lock in router/service/client separation and typed stream contracts.
   - Extend docs to describe architectural boundaries, not just endpoint behavior.
   - Update `PROJECT_STATUS.md`, `API_REFERENCE.md`, and durable agent memory as each boundary migration lands.

Progress already landed in this phase:

- Session persistence, title generation, runtime adapters, and SSE helpers have been extracted into smaller backend boundaries.
- SQLite logging and session history now sit behind injectable interfaces.
- Frontend session orchestration has been moved out of `App.tsx` into a dedicated controller hook.
- Upload validation and request parsing are centralized behind a shared service.
- SSE frames are now typed event objects instead of legacy string sentinels.
- Black-box API contract coverage exists through `__tests__/test_api_blackbox_contract.py`.

---

## Infrastructure Notes

| Item | Current | Target |
|------|---------|--------|
| Server | A100 Ubuntu 24.04 | same |
| Public URL | `https://ai.simonbb.com/mingzhi/` | same (or dedicated subdomain) |
| Port | 62606 (nginx proxy) | 62606 |
| Process mgmt | `nohup` + PID file by default on no-root hosts | `systemd --user` if available; otherwise watchdog/tmux fallback |
| Log files | `logs/fastapi.log` + user-space rotation script | same |
| Node version | 24.14.1 (`.nvmrc`) | 24.x |
| Python | 3.12.6 | 3.12.x |

---

## Decision Log

| Date | Decision | Reason |
|------|----------|--------|
| 2026-03-30 | Use port 62606 instead of 8002 in production | Only 62606 is reachable through school nginx |
| 2026-03-30 | Vite `base: './'` | Required for JupyterHub proxy and nginx sub-path compatibility |
| 2026-03-30 | SSE over WebSocket | Simpler and more proxy-friendly; native browser support |
| 2026-03-30 | No React Router | Single-page app; extra routing complexity had little benefit |
| 2026-03-31 | Dual-port deploy reverted | Production uses `:62606` only |
