# GOAT AI Roadmap

> Last updated: 2026-04-07 — **Phase 11 shipped** in v1.3.0; **Phases 13-14**: 13 = §13.0 + Wave A/B (stable `request_id`, **liveness**/**readiness**, error `code`); 14 = semantics before directory migration (**consumes** §13.0 error model; **does not redefine** it)
> Current release: **v1.3.0**
> Compact snapshot: [PROJECT_STATUS.md](PROJECT_STATUS.md)

---

## Shipped (v1.3.0)

| Phase | Content |
|-------|---------|
| 11 | **Industrialization and decoupling (complete):** `ChatStreamService` owns SSE/tool/safeguard streaming; `chat_orchestration.py` holds `PromptComposer` / `ChartToolOrchestrator` / `SessionPersistenceService`; `chat_service.py` is a thin `stream_chat_sse` entry; injectable `TabularContextExtractor` + `LLMClient.generate_completion` for titles; `log_service` import confined to adapters with architecture guard; wire markers centralized (`CHART_DATA_CSV_MARKER`, `FILE_CONTEXT_UPLOAD_PREFIX`, `LEGACY_CSV_FENCE_SUBSTRING`); `test_architecture_boundaries` runs under `unittest discover` |
| 12 | **Hardening and scale-readiness (complete):** explicit chart data-source policy (`uploaded`/`demo`/`none`), architecture guardrails (backend/frontend + `log_service` confinement), latency p50/p95 with model buckets, expanded `/api/chat` black-box matrix, deploy post-check script, API contract CI sync gate, and model capability TTL cache |

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
| 7 | Quality and observability hardening: user-space log rotation, no-root deploy fallback, backend tests, frontend Vitest, CI, `request_id` / tracing headers, latency metrics |
| 8 | Charting and telemetry: structured `chart_spec`, Apache ECharts `ChartCard`, real A100 GPU telemetry, rolling inference latency, Markdown export, dependency-safe frontend deploys |
| 9 | Access and security: API key protection, rate limiting, `request_id` (`X-Request-ID`), production-safe access controls |
| 10 | Native chart-tool path: constrained `ChartIntentV2` -> `ChartSpecV2` compiler, Ollama tool-capability checks, tool-call-only chart rendering |

### Phase 11 (archived objective — met)

- Align with `AGENTS.md`: typed boundaries, router-thin API, orchestration in services, portable dev/prod.
- **Follow-up (post-Phase 11):** optional deeper migration of legacy session **content** markers (`__chart__`, etc.) into versioned payload-only fields without breaking SQLite rows —not blocking; v2 payload + codec already separate display roles from chat turns.

### Near-term execution order (project-calibrated)

Aligned with `AGENTS.md` and **no-root / JupyterHub-style** production (`docs/OPERATIONS.md`): `systemd --user` when D-Bus works; **nohup + PID remains a permanent fallback**.

| Horizon | Focus |
|---------|--------|
| **v1.3.x** | Ops hardening from Phase 12 backlog: systemd vs nohup playbook, SQLite backup/migration thresholds, security/audit as exposure grows. |
| **v1.4.x** | **Phase 13** — §13.0 (migrations + error model), **Wave A** (structured logs + `request_id`, Prometheus metrics, **readiness** vs **liveness**, persistence failure signals), then **Wave B** (Ollama resilience, **idempotency**); SLO/load, backup, security/CI. **Postgres / multi-instance** only after Phase 13 exit criteria and v1.3.x ops gates are stable. Low-risk Phase 14 doc-only items may run in parallel when isolated. |
| **v1.5+** | **Phase 14** —domain/application split, test harness + integration tier, optional message normalization & distributed tracing (**consumes** Phase 13 §13.0 error model; **does not redefine** it). |

---

### Phase 12 (archived objective — met)

- Scope achieved: guardrails for architecture boundaries, telemetry quality, API contract stability, and deploy acceptance checks are in place.
- Verification artifacts:
  - Orchestration split and collaborators: `backend/services/chat_stream_service.py`, `backend/services/chat_orchestration.py`, `backend/services/chat_service.py`
  - Chart source policy and persistence: `backend/services/session_message_codec.py`, `backend/services/session_service.py`
  - Architecture boundaries: `__tests__/test_architecture_boundaries.py`
  - Latency p50/p95 + model buckets: `goat_ai/latency_metrics.py`, `backend/services/system_telemetry_service.py`
  - `/api/chat` black-box matrix: `__tests__/test_api_blackbox_contract.py`
  - Deploy post-check: `scripts/post_deploy_check.py`
  - Contract CI gate: `tools/check_api_contract_sync.py`, `.github/workflows/ci.yml`
  - Model capability TTL cache: `goat_ai/ollama_client.py`, `__tests__/test_ollama_client_cache.py`

---

## Phase 13: Industrial 9/10 — Priority 1 (Run, Observe, Recover)

**Target release band:** **v1.4.x**  
**Goal:** Production-grade **signals**, **stable error semantics**, **deploy** (**liveness** / **readiness**), **capacity clarity**, and **data/security baselines** on **SQLite + no-root + Ollama**—without large directory refactors (those stay in Phase 14).

**Done for Phase 13:** exit criteria met per subsection; `PROJECT_STATUS.md` / release notes cite which boxes closed.

### 13.0 Cross-cutting prerequisites (before Wave A)

These are **not** "nice-to-have data tasks" — they unblock schema evolution and every downstream observability/reliability decision.

- `[x]` **Migrations as artifacts** —`backend/migrations/` numbered SQL, applied in order at startup via `backend.services.db_migrations`; `schema_migrations` table stores SHA-256 checksums (tamper detection). **Landed:** `log_service.init_db` delegates to `apply_migrations`; `__tests__/test_db_migrations.py`.
- `[x]` **Error model + exception registry** —Stable JSON `{ "detail", "code", "request_id" }`; `backend/api_errors.py` + `register_exception_handlers` in `backend/exception_handlers.py`; middleware 401/429 use same envelope; `X-Request-ID` honored when client sends it. **Landed:** `docs/API_ERRORS.md`, OpenAPI `ErrorResponse`, black-box assertions. **Follow-up:** per-route log level / metric label table remains Wave A-B.

*Why this order:* structured logs and metrics need **stable `code` / classification**; **readiness** / **liveness** and runbooks need **consistent failure surface**; later Wave B retries need **explicit retryability** on errors.

### Wave A — operational lift (exactly four)

**Scope lock:** Wave A is **only** these four. Do **not** bundle Ollama retry/circuit breaker here — client resilience is **Wave B** so it does not steal observability delivery rhythm.

**Terminology:** Use **`request_id`** (header `X-Request-ID`, context `goat_ai.request_context`), **liveness** (`GET /api/health`), **readiness** (`GET /api/ready`), and **idempotency** (Wave B) consistently — not loose synonyms.

#### Verifiable thresholds (Wave A)

- **A1** —At least one documented structured log line includes fields **`ts`**, **`level`**, **`message`**, **`request_id`** (when bound); ERROR / persistence lines SHOULD also carry **`code`** and **`event`** where applicable (see `docs/OPERATIONS.md`).
- **A2** —Minimum Prometheus **label** sets: `http_requests_total` →`method`, `route`, `status`; `http_request_duration_seconds` histogram →`le` on buckets (plus `_sum` / `_count`); `chat_stream_completed_total` →none (**successful completion only; safeguard-blocked refusal flows excluded**); `ollama_errors_total` →`code`, `endpoint`, `http_status`; `sqlite_log_write_failures_total` →`operation`, `code`.
- **A3** —**`/ready` not ready:** HTTP **503**; JSON body **`{ "ready": false, "checks": { ... } }`** with stable keys `settings`, `sqlite`, `ollama`. Structured ERROR logs for probe failures use fixed **`code`** values **`SQLITE_READINESS_FAILED`** and **`OLLAMA_READINESS_FAILED`** (see `backend/readiness_service.py`).
- **A4** —Failure injection / proof: **`__tests__/test_log_service_wave_a.py`** (mocked SQLite fault + metric hook assertion); counter appears in `GET /api/system/metrics` text in integration/black-box runs.

| # | Deliverable | Primary artifact | Owner | Exit criterion |
|---|-------------|------------------|-------|----------------|
| **A1** | **`[x]` Structured logging + `request_id` context** —JSON (or key=value) behind `GOAT_LOG_JSON=1`; honor inbound `X-Request-ID`; bind id in `contextvars` (`goat_ai.request_context`). | `docs/OPERATIONS.md`; `goat_ai/logging_config.py`; `goat_ai/request_context.py`; `backend/exception_handlers.py` | Backend + ops | Sample + field contract in OPERATIONS; ERROR / JSON errors share `request_id`; handlers set `X-Request-ID`. |
| **A2** | **`[x]` Metrics** —`GET /api/system/metrics` (Prometheus text): `http_requests_total`, `http_request_duration_seconds`, `chat_stream_completed_total`, `ollama_errors_total`, `sqlite_log_write_failures_total`. | `backend/prometheus_metrics.py`; `goat_ai/telemetry_counters.py`; `__tests__/test_api_blackbox_contract.py` (`test_metrics_endpoint_prometheus_text`) | Backend + ops | OPERATIONS scrape note; black-box asserts required metric names. |
| **A3** | **`[x]` Readiness vs liveness** —**`/api/health`** = **liveness**; **`GET /api/ready`** = **readiness** (SQLite + optional Ollama probe; `GOAT_READY_SKIP_OLLAMA_PROBE`). | `backend/readiness_service.py`; `scripts/post_deploy_check.py`; `__tests__/test_api_blackbox_contract.py` (`test_ready_endpoint_contract`) | Backend + ops | Post-deploy script requires `/ready`; black-box tests public **readiness** path. |
| **A4** | **`[x]` Persistence failure signals** —On `log_service` session/conversation write failure: structured ERROR + `sqlite_log_write_failures_total` (**SSE** may still complete). | `backend/services/log_service.py`; `__tests__/test_log_service_wave_a.py` | Backend | Tests + metrics text include `sqlite_log_write_failures_total`. |

### Wave B — client & API resilience (after Wave A)

| # | Deliverable | Verifiable threshold (target) | Primary artifact | Owner | Exit |
|---|-------------|-------------------------------|------------------|-------|------|
| **B1** | `[x]` **Ollama client policy** —Retries with backoff + jitter for **idempotent** reads (`/api/tags`, `/api/show`); timeouts unchanged; circuit breaker (open / half-open). Registry **retryability** from §13.0. | Mocked HTTP tests prove backoff + breaker states without live Ollama. | `goat_ai/ollama_client.py`; `__tests__/` (new or extended); `docs/OPERATIONS.md` | Backend | OPERATIONS table + tests. |
| **B2** | `[x]` **Idempotency** —Optional `Idempotency-Key` for **upload analyze JSON** and **session append** (SQLite TTL table or in-process LRU for single-node). | Duplicate key →same response body / no double write (black-box). | Relevant routers + services; `__tests__/test_api_blackbox_contract.py` (or sibling) | Backend | Black-box duplicate-key test. |
| **B3** | `[x]` **Multi-instance stance** —OPERATIONS: in-memory limiter + rolling metrics are **per-process**; mitigations without Redis (sticky sessions, lower per-instance limits, external metrics aggregation). | Doc lists limitations + mitigations; no false "cluster-wide" claims. | `docs/OPERATIONS.md` | Ops + backend | Published limitations. |

### 13.3 Performance and capacity

- `[x]` **Published SLOs** —Table in OPERATIONS: first-token p95 budget, max concurrent SSE, max session payload / message count, upload time budget. **Exit:** linked from README.
- `[x]` **Load script** —`tools/load_chat_smoke.py` or k6 + runbook; p50/p95 from `/api/system/inference` + RSS note. **Exit:** one command documented.
- `[x]` **Hot path guardrails** —Profile chart compile + session JSON path; **max messages** or size →**422 or explicit truncate** (no silent corruption). **Exit:** documented + test.

### 13.4 Data and state (post-migration-tooling)

- `[x]` **Audit fields on sessions** —`schema_version`, `updated_at` (and safe extras); history API exposes only non-sensitive fields. **Exit:** contract + test (migrations from §13.0 carry the DDL).
- `[x]` **Backup / restore runbook** —`test_backup_chat_db` →OPERATIONS (`sqlite3 .backup`, integrity, restore drill). **Exit:** linked one-pager.

### 13.5 Security and tooling

- `[x]` **Dependency audit in CI** —`pip-audit` on `requirements.txt`; fail vs warn policy documented. **Landed:** CI workflow step, pinned vulnerable dependencies updated, audit passes clean on the current lock set.
- `[x]` **Upload / API threat notes** —`docs/SECURITY.md`: extensions vs sniff, zip bombs, CSV formula injection, shared API key model. **Landed:** OPERATIONS links it and documents the shared-key trust model.
- `[x]` **Python lint/format in CI** —`ruff check` + `ruff format` on changed Python files (equivalent to a full-repo rewrite-free formatting gate). **Landed:** CI workflow step plus `ruff` config-compatible checks.

### 13.6 Release and operations (beyond Wave A)

- `[x]` **Graceful shutdown** —Uvicorn/SSE drain expectations and max wait. **Exit:** OPERATIONS.
- `[x]` **Rollback runbook** —Previous tag + venv + DB backup + post-deploy check. **Exit:** OPERATIONS link.

### 13.7 Phase 13 non-goals

- Postgres / Redis **solely** to close Phase 13 —optional; Decision Log if introduced.
- Full multi-tenant IAM —optional one-page threat model for shared API key is enough for Phase 13.

### 13.8 Risk triggers (Phase 13 execution)

| Trigger | Response |
|---------|----------|
| **SSE** error rate or timeout above agreed threshold | Pause **Wave B** (client retry / **idempotency**) until root cause triaged. |
| **`/api/ready`** flapping or sustained non-200 in prod | Block **Phase 14** structural refactors until **readiness** and deploy checks are stable. |
| **`sqlite_log_write_failures_total`** (or equivalent) abnormal for a sustained window | Prioritize recovery + backup/restore drill before new persistence features. |

---

## Phase 13.9: Native Multimodal Capability Expansion

**Target release band:** **late v1.4.x**, after Phase 13 exit criteria are stable and before Phase 14 structural refactors begin.
**Goal:** Add **native image and video understanding** for Ollama models that explicitly support multimodal inputs, without weakening the existing text/chat contract or introducing silent fallback behavior.

**Ordering principle:** **vision first, video second**. Treat image support as the MVP and video as a follow-on that can reuse the same capability contract, media-context pipeline, and SSE response model.

### 13.9.1 Capability contract and model gating

- `[ ]` **Explicit multimodal capabilities** —Extend model capability probing so the backend can distinguish `text`, `vision`, `video`, and `multimodal` support.
- `[ ]` **Contract-first gating** —Expose multimodal support through the same black-box style contract used for chat/model capabilities; the UI must disable unsupported media flows instead of silently degrading them.
- `[ ]` **Capability-aware model selection** —Surface a clear capability badge or equivalent UI signal so users can tell whether the currently selected model can read images or video.

### 13.9.2 Image understanding MVP

- `[ ]` **Image upload path** —Add a typed upload flow for images (`png`, `jpg/jpeg`, `webp` initially) with size limits, preview, and explicit attachment state.
- `[ ]` **Media context service** —Create a backend service that normalizes image inputs, applies safe resizing/encoding, and converts them into the Ollama message format expected by native multimodal models.
- `[ ]` **Chat integration** —Extend `POST /api/chat` so image attachments become first-class chat context instead of ad hoc prompt text.
- `[ ]` **Failure behavior** —If the selected model does not support vision, return a clear, sanitized error and keep the text-only chat path intact.

### 13.9.3 Video understanding follow-on

- `[ ]` **Video upload path** —Add a typed upload flow for video files with clear size/duration guardrails.
- `[ ]` **Frame extraction pipeline** —Implement a backend media pipeline that extracts representative frames and timestamps, then packages them as ordered multimodal context.
- `[ ]` **Optional audio companion context** —If supported by the chosen implementation, add transcript or scene-summary context as a separate structured input rather than mixing it into the chat prompt.
- `[ ]` **Native video gating** —Only enable direct video understanding when the selected model and backend pipeline both explicitly support it; otherwise, keep the feature disabled.

### 13.9.4 Frontend experience

- `[ ]` **Attachment UX** —Add image/video attachments to the chat composer with preview, removal, and clear status labels.
- `[ ]` **User-facing model hints** —Show whether the current model can inspect uploaded media, and explain when an attachment is not usable by the selected model.
- `[ ]` **No silent fallback** —Do not auto-convert media into hidden OCR/ASR text unless that behavior is intentionally exposed as a separate, explicit feature.

### 13.9.5 Tests and release criteria

- `[ ]` **Black-box contract tests** —Cover supported and unsupported multimodal requests at the API boundary, including image input success, video input success, and clean rejection for unsupported models.
- `[ ]` **Service tests** —Unit test media normalization, capability gating, frame selection, and error handling without live Ollama dependencies.
- `[ ]` **Operational readiness** —Document multimodal timeout, size, and format limits in OPERATIONS before enabling the UI entry points.

---

## Phase 14: Industrial 9/10 —Priority 2 (Semantics, Then Structure)

**Target release band:** **v1.5+** (may overlap **late v1.4.x** for low-risk doc-only items)  
**Goal:** **Semantic convergence first, directory migration second**—policies and invariants stabilize meaning before `application/` vs `domain/` vs `infra/` reshaping. Phase 14 **consumes** the Phase 13 §13.0 **error model** (stable `code`, `request_id`, handlers); it **does not redefine** that contract—only uses it for policies, tests, and optional tracing.

**Ordering principle (industrial default):** policy objects + invariants = **narrow, testable moves**; package reshuffle = **wide blast radius**. Do the former first.

### 14.1 Domain semantics and policy objects (before big split)

- `[ ]` **`docs/DOMAIN.md`** —Ubiquitous language: Session, Turn, FileContext, ChartIntent, ChartSpec, ToolCall, SafeguardDecision. **Exit:** PR template links for user-visible behavior changes.
- `[ ]` **`SafeguardPolicy`** (or equivalent) —Typed inputs →decision; unit tests **without** HTTP. **Exit:** orchestration calls policy object, not ad hoc string rules.
- `[ ]` **`ChartDataProvenancePolicy`** —Same: explicit provenance decisions vs implicit marker logic. **Exit:** tests without HTTP.
- `[ ]` **Invariants** —Small pure helpers: e.g. chart spec persisted only with version; at most one file-context row semantics; failures are test-visible. **Exit:** tests fail when invariant broken.

### 14.2 Large structural migration (after §14.1)

- `[ ]` **Application / domain / infrastructure layout** —`backend/application/`, `backend/domain/`, adapters under clear names; `services/` as facades during migration; **update `import-linter` layers**. **Exit:** dependency graph doc; no new business rules in `routers/`.
- `[ ]` **Session schema contract** —`docs/SESSION_SCHEMA.md`: message JSON version, read N- / write N, codec upgrade tests. **Exit:** round-trip old →new row tests (builds on Phase 13 migrations).
- `[ ]` **Ports list** —AGENTS.md: stable `Protocol`s (`SessionRepository`, `LLMClient`, telemetry sink); one **fake repository** test without SQLite file.

### 14.3 Testability

- `[ ]` **Clock / random injection** —`Clock` (wall + monotonic) for TTL, rate limit, title paths; optional seeded RNG. **Exit:** no `time.sleep` for those behaviors.
- `[ ]` **Single primary test entry** —**pytest** as primary for `__tests__/`; unittest shimmed where needed. **Exit:** one CI command documented.
- `[ ]` **Integration tier** —`__tests__/integration/`: temp SQLite + `TestClient` for session + migrations (no Ollama). **Exit:** CI or optional job; under 30s runtime budget documented.

### 14.4 Data (deep)

- `[ ]` **Message store normalization** —`session_messages` (append-only); dual-read from legacy JSON until cutover. **Exit:** migration doc + integration tests.

### 14.5 Security (deeper)

- `[ ]` **AuthZ roadmap + enforcement** —Scoped keys or session ownership in **service** layer; Decision Log entry. **Exit:** minimal cross-session denial tests.
- `[ ]` **Secrets hygiene automation** —Optional Gitleaks/trufflehog in CI; CONTRIBUTING: `.env.example` review on env changes.

### 14.6 Observability (optional stretch)

- `[ ]` **Distributed tracing** —OpenTelemetry + W3C `traceparent`; spans around Ollama; off by default, near-zero cost when disabled. **Exit:** one documented trace export path.

### 14.7 Phase 14 references

- [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md) · [OPERATIONS.md](OPERATIONS.md) · [AGENTS.md](../AGENTS.md)

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
| 2026-04-07 | Phases 13-14 split from prior monolithic Phase 13 | **13** = priority 1; **14** = priority 2 (semantics before package reshuffle). |
| 2026-04-07 | Phase 13 sequencing tightened | **§13.0** = migrations-as-artifacts + error model/registry **before** Wave A. **Wave A** = only four ops items (structured logs+`request_id`, metrics, **liveness**/**readiness**, persistence signals). **Ollama retry/circuit breaker** deferred to **Wave B** after Wave A. **Phase 14** = policy objects + invariants **before** `application/`/`domain/` split; **consumes** §13.0 error model, **does not redefine** it. |
| 2026-04-08 | Phase 13.5 closed | `pip-audit` added to CI, `ruff check` added to CI, changed-file `ruff format` gate added, `docs/SECURITY.md` published, and known vulnerable dependency pins updated (`requests`, `python-multipart`). |
| 2026-04-08 | Phase 13.6-13.8 closed | Graceful shutdown is now documented and implemented in deploy scripts; rollback has an explicit ref-aware runbook; Phase 13 risk triggers are documented in OPERATIONS. |
