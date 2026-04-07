# GOAT AI Roadmap

> Last updated: 2026-04-07 — **Phase 11 shipped** in v1.3.0; API black-box re-verified (79 + 13 tests)
> Current release: **v1.3.0**
> Compact snapshot: [PROJECT_STATUS.md](PROJECT_STATUS.md)

---

## Shipped (v1.3.0)

| Phase | Content |
|-------|---------|
| 11 | **Industrialization and decoupling (complete):** `ChatStreamService` owns SSE/tool/safeguard streaming; `chat_orchestration.py` holds `PromptComposer` / `ChartToolOrchestrator` / `SessionPersistenceService`; `chat_service.py` is a thin `stream_chat_sse` entry; injectable `TabularContextExtractor` + `LLMClient.generate_completion` for titles; `log_service` import confined to adapters with architecture guard; wire markers centralized (`CHART_DATA_CSV_MARKER`, `FILE_CONTEXT_UPLOAD_PREFIX`, `LEGACY_CSV_FENCE_SUBSTRING`); `test_architecture_boundaries` runs under `unittest discover` |

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

### Phase 11 (archived objective — met)

- Align with `AGENTS.md`: typed boundaries, router-thin API, orchestration in services, portable dev/prod.
- **Follow-up (post–Phase 11):** optional deeper migration of legacy session **content** markers (`__chart__`, etc.) into versioned payload-only fields without breaking SQLite rows — not blocking; v2 payload + codec already separate display roles from chat turns.

### Near-term execution order (project-calibrated)

Aligned with `AGENTS.md` and **no-root / JupyterHub-style** production (`docs/OPERATIONS.md`): `systemd --user` when D-Bus works; **nohup + PID remains a permanent fallback**.

| Horizon | Focus |
|---------|--------|
| **v1.3.x** | Ops hardening from Phase 12 backlog: systemd vs nohup playbook, SQLite backup/migration thresholds, security/audit as exposure grows. |
| **v1.4** | Evaluate Postgres / jobs / multi-instance **after** ops gates from v1.3.x are stable. |

---

## Phase 12: Hardening and Scale Readiness

Status legend:
- `[ ]` Not started
- `[~]` In progress
- `[x]` Completed

Objective:
- Convert the recently stabilized contracts into durable guardrails so performance, architecture boundaries, and deploy behavior remain stable as features scale.

Execution plan:

1. `[x]` Decompose backend chat orchestration into focused collaborators
   - **Landed:** `PromptComposer`, `ChartToolOrchestrator`, and `SessionPersistenceService` in `chat_orchestration.py`; **`ChatStreamService`** in `chat_stream_service.py`; thin `stream_chat_sse` in `chat_service.py`. SSE contract preserved.

2. `[x]` Introduce explicit chart data-source policy models
   - Add typed chart data source metadata (`uploaded`, `demo`, `none`) instead of implicit marker-driven behavior.
   - Persist source provenance with session history for debugging and auditability.

3. `[x]` Add architecture guard tests (backend + frontend)
   - Lock in backend layer boundaries (router/service/shared layer import rules).
   - Lock in frontend boundary rule that hooks do not import components.
   - **`log_service` confinement:** only `log_service.py` and `chat_runtime.py` may import `log_service` under `backend/services/` (enforced in `test_architecture_boundaries`).

4. `[x]` Define latency SLOs with percentile telemetry
   - Extend telemetry from rolling mean to include p50/p95 for chat completion and first-token latency.
   - Add model-aware buckets to catch regressions by model family.

5. `[x]` Expand `/api/chat` black-box scenario matrix
   - Cover uploaded vs non-uploaded chart prompts, tools-supported vs tools-unsupported models, and mixed-language chart intents.
   - Keep assertions centered on typed SSE contract behavior.

6. `[x]` Add deploy post-check acceptance script
   - Validate health, runtime-target contract, and typed stream behavior immediately after deploy.
   - Fail fast when process is alive but contract is broken.

7. `[x]` Enforce docs-and-contract CI gate
   - Require synchronized updates for `docs/openapi.json`, `docs/api.llm.yaml`, and black-box tests when API payloads change.
   - Prevent drift between runtime behavior and committed contract artifacts.

8. `[x]` Add model capability cache with TTL

Progress already landed in this phase:

- Backend chat orchestration uses `ChatStreamService` plus collaborators (`PromptComposer`, `ChartToolOrchestrator`, `SessionPersistenceService`) while preserving `/api/chat` SSE contract behavior (Phase 11 complete).
- Chart rendering policy is now explicit about data source provenance (`uploaded`, `demo`, `none`) and persisted in session payloads.
- Architecture guard tests lock backend and frontend layer boundaries to reduce regression risk.
- Inference telemetry now exposes rolling average + p50/p95 for completion and first-token latency, including model-scoped buckets.
- Black-box API coverage now includes chart tool behavior for uploaded and non-uploaded scenarios as well as tools-unsupported models.
- Deploy scripts now run post-deploy contract checks before declaring success.
- CI now blocks drift between runtime API contracts and committed `docs/openapi.json` + `docs/api.llm.yaml`.
- Ollama model capability checks now use a configurable TTL cache to reduce repetitive capability probes.
   - Cache tool-capability probes to reduce repeated upstream capability checks.
   - Keep cache boundaries explicit and invalidate safely on model list changes.

---

## Infrastructure Notes

| Item | Current | Target |
|------|---------|--------|
| Server | A100 Ubuntu 24.04 | same |
| Public URL | `https://ai.simonbb.com/mingzhi/` | same (or dedicated subdomain) |
| Port | 62606 (nginx proxy) | 62606 |
| Process mgmt | `nohup` + PID file default on no-root hosts (required fallback) | Try `systemd --user` when D-Bus/session is available; **always** retain nohup/watchdog path for SSH/JupyterHub hosts where user systemd fails |
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
| 2026-04-07 | Process mgmt: systemd is additive, not a drop-in for nohup | Shared host may lack reliable `systemctl --user`; deploy contract keeps nohup + PID as permanent fallback per `AGENTS.md` / `OPERATIONS.md` |
| 2026-04-07 | Phase 11 closed in v1.3.0 | `ChatStreamService` + orchestration split; tabular/title injection; log_service adapter-only guard; wire constants centralized; 79 unittest + 13 black-box OK |
