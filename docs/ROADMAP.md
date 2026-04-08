# GOAT AI Roadmap

> Last updated: 2026-04-09 — **v1.3.0** tags Phase **11–12**; **main** additionally ships **Phase 13** (full closeout) and **Phase 14** through **14.6 RAG-3**. **Phase 15.2–15.7** slices through **15.6** are complete on main (session store normalization, AuthZ keys + owner header, optional OTel). **Next:** further **Phase 15** structural work as listed below §15.7; keep the **§14.7** RAG eval gate green as retrieval evolves. **Constraints vs roadmap:** see [Current reality and improvement map](#current-reality-and-improvement-map).
> Current release tag: **v1.3.0**
> Compact snapshot: [PROJECT_STATUS.md](PROJECT_STATUS.md) · Engineering standards: [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md)

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

### Archived objectives (met; detail folded into phase tables above)

| Phase | One-line outcome |
|-------|------------------|
| 11 | Typed boundaries, thin routers, orchestration in services, portable dev/prod per [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md). Optional follow-up: migrate legacy session content markers into versioned payload fields — not blocking. |
| 12 | Architecture boundary guardrails, telemetry quality, API contract stability, deploy acceptance checks. |

---

## Completed on main (post–v1.3.0 tag)

Work below is **landed on main**; see [PROJECT_STATUS.md](PROJECT_STATUS.md) for the live inventory. Release tagging may trail.

### Phase 13 — Industrial 9/10 (Priority 1): **complete**

| Slice | Status | Summary |
|-------|--------|---------|
| **§13.0** | Done | Numbered SQL migrations + `schema_migrations` checksums; stable JSON errors `{ detail, code, request_id }` + handlers; `X-Request-ID` honored. |
| **Wave A** | Done | Structured logging + `request_id`; Prometheus metrics (`http_requests_total`, durations, `chat_stream_completed_total`, `ollama_errors_total`, `sqlite_log_write_failures_total`); liveness `/api/health` vs readiness `/api/ready`; persistence failure signals + tests. |
| **Wave B** | Done | Ollama retries + circuit breaker on idempotent reads; optional `Idempotency-Key` (upload analyze + session append); multi-instance limitations documented in OPERATIONS. |
| **13.3** | Done | SLO table, load smoke (`tools/load_chat_smoke.py`), chat hot-path size/count guardrails (`422` / explicit behavior). |
| **13.4** | Done | Session audit fields (`schema_version`, `updated_at`); backup/restore runbook. |
| **13.5** | Done | `pip-audit` + `ruff` in CI; [SECURITY.md](SECURITY.md). |
| **13.6** | Done | Graceful shutdown + rollback runbook. |

### Phase 14 — RAG-first expansion: **through RAG-3 complete**

| Slice | Status | Summary |
|-------|--------|---------|
| **14.1 Baseline** | Done | Non-goals retired; `knowledge/*` API family; contract-first black-box coverage; `simple_local_v1` storage gate documented. |
| **14.2 RAG-0** | Done | Dedicated `/api/knowledge/*` family; OpenAPI routes for uploads, ingestions, search, answers; chat uses explicit `knowledge_document_ids` only. |
| **14.3 RAG-1** | Done | Persisted uploads under `GOAT_DATA_DIR`, migration `007`, normalize/chunk CSV/XLSX/TXT/MD/PDF/DOCX, embeddings + local vector index, ingestion status API; legacy `/api/upload` + `/api/upload/analyze` on knowledge pipeline. |
| **14.4 RAG-2** | Done | `POST /api/knowledge/search`, `POST /api/knowledge/answers`, chat integration, no-hit + fallback behaviors, black-box coverage. |
| **14.5 Vision MVP** | Done | Capability signal + `POST /api/media/uploads`, `image_attachment_ids` on chat, media service + vision routing, frontend attach UX, black-box + ops limits. |
| **14.6 RAG-3** | Done | Rerank + query-rewrite `Protocol` seams, `retrieval_profile` (`default` / `rag3_lexical` / `rag3_quality`), `evaldata/` + `tools/run_rag_eval.py`, README/PROJECT_STATUS quality gate. |

---

## Next implementation direction

Program order for remaining roadmap:

| Order | Focus | Notes |
|-------|--------|--------|
| **0** | **§14.7 RAG quality closure** | CI/regression eval, thresholds, golden-set process, light observability — see [§14.7](#147-rag-quality-closure-post-146--in-progress--next). |
| **1** | **Phase 15** | `DOMAIN.md`, policy objects, then one-time `application` / `domain` / `infrastructure` split; pytest-first, integration tier; optional `session_messages`, minimal AuthZ, optional OpenTelemetry. |

### Near-term execution order (project-calibrated)

Aligned with [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md) and **reference** no-root / JupyterHub-style deployments among others (`docs/OPERATIONS.md` **Deployment profiles**): `systemd --user` when D-Bus works; **nohup + PID remains a permanent fallback** where applicable.

| Horizon | Focus |
|---------|--------|
| **v1.3.x** | Ops hardening from Phase 12 backlog: systemd vs nohup playbook, SQLite backup/migration thresholds, security/audit as exposure grows. |
| **v1.4.x** | Phase 13 is **done on main**; any follow-up is maintenance. Postgres / multi-instance only after ops gates stable. |
| **v1.5.x** | Phase **14** (through **14.6**) and **Vision MVP** are **ship-complete on main**; active follow-up is **§14.7** (RAG quality closure), then **Phase 15**. |
| **v1.6+** | **Phase 15** — semantics and structural overhaul, optional normalization & tracing (**consumes** Phase 13 §13.0 error model; **does not redefine** it). May overlap late **v1.5.x** once **§14.7** exit criteria are clear. |

---

## Current reality and improvement map

This section records **constraints that match today’s shipped architecture** and **where planned improvements sit** in this roadmap (phases, docs, or decision log). It does not replace exit criteria in individual phases.

### 1. Access control — shared API key (no per-user AuthN/AuthZ)

| Reality (main) | Improvement path | Roadmap / docs home |
|----------------|------------------|---------------------|
| Protection is **`GOAT_API_KEY` + `X-GOAT-API-Key`** when set; optional **`GOAT_API_KEY_WRITE`** splits read vs write HTTP methods; optional **`X-GOAT-Owner-Id`** + **`GOAT_REQUIRE_SESSION_OWNER`** scopes sessions (not end-user AuthN). | **Document** threat model, rotation, and blast radius; keep rate limits and health exceptions as today. | [SECURITY.md](SECURITY.md), [OPERATIONS.md](OPERATIONS.md); Phase **15.5** minimal enforcement. |
| Feature gates expose **`policy_allowed: null`** until richer AuthZ exists; runtime gating (503) is separate from policy (403). | Scoped keys + owner header are **opt-in** via env; **not** full IAM until product requires it. | [test_api_authz.py](../__tests__/test_api_authz.py); [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md) §15. |
| Per-user sessions in SQLite are **not** authenticated identities; `owner_id` is a **convenience partition**, not proof of principal. | Stricter identity would require a Decision Log + product commitment. | [SESSION_MESSAGES_MIGRATION.md](SESSION_MESSAGES_MIGRATION.md); Decision Log 2026-04-08. |

**Priority:** Docs + operational discipline **first**; code changes for multi-key **only** when exposure grows (see horizon **v1.3.x** in [Near-term execution order](#near-term-execution-order-project-calibrated)).

### 2. Data plane — SQLite + local vector index (`simple_local_v1`)

| Reality (main) | Improvement path | Roadmap / docs home |
|----------------|------------------|---------------------|
| **Single primary SQLite** for app metadata; **files + JSON vector artifacts** under `GOAT_DATA_DIR`; not a multi-writer cluster store. | Treat **one active writer** as the supported deployment; document backup/restore and migration discipline. | [OPERATIONS.md](OPERATIONS.md), [BACKUP_RESTORE.md](BACKUP_RESTORE.md); Phase **13** Wave B “multi-instance limitations”; Appendix [RAG subsystem](#appendix-rag-subsystem-architecture-snapshot). |
| Horizontal scale-out **not** a current goal; multiple Uvicorn workers or multiple hosts require a **Decision Log** + storage change. | **If** capacity forces it: Postgres (or equivalent) + optional external vector store — **after** ops stability gates (Phase **13** risk triggers). | Phase **13** non-goals; new Decision Log entry before any migration; not Phase 15’s default outcome. |

**Priority:** Correct **single-instance** ops and backups **before** distributed data stores.

### 3. RAG quality — protocols shipped; §14.7 closure landed

| Reality (main) | Improvement path | Roadmap / docs home |
|----------------|------------------|---------------------|
| **14.6** delivered rerank/rewrite **Protocols**, `retrieval_profile`, `tools/run_rag_eval.py`, `evaldata/`. | **§14.7:** CI runs `run_rag_eval.py` every backend build; OPERATIONS documents knobs; `evaldata/README.md` + `VERSION`; metrics on profile/outcome and rewrite. | **§14.7** below; [README.md](../README.md) / [PROJECT_STATUS.md](PROJECT_STATUS.md) “RAG-ready” wording. |
| Further tuning (score cutoffs, dashboards) | Optional; not blocking §14.7. | Phase **15.6** optional. |

**Priority:** **§14.7** is complete; iterate eval cases as retrieval behavior evolves.

### 4. Testing — black-box strong; integration + clock partially landed

| Reality (main) | Improvement path | Roadmap / docs home |
|----------------|------------------|---------------------|
| Contract tests and architecture guards exist; many flows use mocks. | **Integration tier (initial):** `__tests__/integration/` with temp `GOAT_LOG_PATH` / `GOAT_DATA_DIR`, `TestClient`, `GOAT_READY_SKIP_OLLAMA_PROBE`; pytest marker `integration`; ~30s budget in [SESSION_SCHEMA.md](SESSION_SCHEMA.md) / [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md). Expand coverage as needed. | Phase **15.3** (first exit met); [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md) testing rules. |
| Clock / RNG not fully injected everywhere. | **`Clock`** (`goat_ai/clocks.py`) injected for **idempotency** TTL; thread through chat/rate-limit/title paths in follow-ups. Optional seeded RNG remains future work. | Phase **15.3** (narrow scope done). |

**Priority:** **High** leverage — lowers cost of §14.7 and Phase **15.1** invariant tests.

### 5. Domain semantics, policy, invariants — partially in code, not fully documented

| Reality (main) | Improvement path | Roadmap / docs home |
|----------------|------------------|---------------------|
| Rules spread across services, prompts, and env; chart/safeguard behavior partially implicit. | **`docs/DOMAIN.md`** + small **policy** types + **invariant** helpers with unit tests **before** large package moves. | Phase **15.1**–**15.2**; PR template link in **15.1** exit criteria. |

**Priority:** **Before** `application`/`domain`/`infra` reshuffle (Phase **15.2**).

### 6. Deployment — shared host, not a platform runtime

| Reality (main) | Improvement path | Roadmap / docs home |
|----------------|------------------|---------------------|
| No root; **`nohup` + PID** is the permanent fallback; `systemd --user` when it works. Process lifecycle is **ops scripts**, not Kubernetes-style orchestration. | Harden **deploy**, **readiness**, **graceful shutdown**, log rotation; document failure modes; avoid assuming `systemctl` in SSH sessions. | [OPERATIONS.md](OPERATIONS.md) **Deployment profiles**; [Infrastructure Notes](#infrastructure-notes); Phase **13.6** done; Decision Log **2026-04-07**. |
| “Platform-grade” self-healing is **out of scope** unless hosting changes. | Revisit only if deployment environment changes (e.g. managed VM with guaranteed systemd). | Decision Log; not Phase 15 default. |

**Priority:** **Reliability of the current path** over new orchestration layers.

### Summary — where work lands

| Theme | Primary roadmap anchor |
|-------|-------------------------|
| Shared key + future minimal AuthZ | §15.5, §15.1, SECURITY / OPERATIONS |
| Single-instance SQLite + local vector | Appendix, OPERATIONS, Phase 13 risk triggers; future datastore = Decision Log |
| RAG eval + thresholds + CI | **§14.7** (complete — CI + OPERATIONS + evaldata + metrics) |
| Integration smoke + clock (idempotency) | §15.3 (initial); broader injection follow-up |
| DOMAIN.md + policy + invariants | §15.1–15.2 |
| Deploy / process lifecycle | Infrastructure Notes, OPERATIONS, Phase 13 closed slices |

---

## Phase 13: Industrial 9/10 — Priority 1 (Run, Observe, Recover) — **closed**

**Target release band:** **v1.4.x**  
**Status:** Exit criteria met; summary table above. Detail: migrations, error model, Wave A/B, SLOs, backup, CI security, graceful shutdown — see [PROJECT_STATUS.md](PROJECT_STATUS.md) and [OPERATIONS.md](OPERATIONS.md).

### Phase 13 risk triggers (retained)

| Trigger | Response |
|---------|----------|
| **SSE** error rate or timeout above agreed threshold | Pause **Wave B** work until root cause triaged. |
| **`/api/ready`** flapping or sustained non-200 in prod | Block **Phase 15** structural refactors until **readiness** and deploy checks are stable. |
| **`sqlite_log_write_failures_total`** (or equivalent) abnormal for a sustained window | Prioritize recovery + backup/restore drill before new persistence features. |

### Phase 13 non-goals (unchanged)

- Postgres / Redis **solely** to close Phase 13 — optional; Decision Log if introduced.
- Full multi-tenant IAM — optional one-page threat model for shared API key is enough for Phase 13.

---

## Phase 14: RAG-first Capability Expansion

**Target release band:** **v1.5.x**  
**Goal:** RAG subsystem with dedicated contracts; **Vision MVP** and **RAG-3 quality** are complete on main.

**Status:** **RAG-0 → RAG-3 complete** on main (tables above). **Next:** Phase 15.

**Priority order (remaining):** **§14.7** (RAG quality closure), then **Phase 15**.

### 14.5 Vision MVP (after retrieval exists) — **complete**

**Scope rule:** image support is the only multimodal slice in this roadmap. Video is out of scope.

- `[x]` **Explicit vision capability contract** —Extend model capability probing so the backend can distinguish `text` and `vision` support, and gate image flows cleanly.
- `[x]` **Capability-aware model selection** —Surface a clear UI signal showing whether the current model can inspect images.
- `[x]` **Image upload path** —Add a typed upload flow for images (`png`, `jpg/jpeg`, `webp` initially) with size limits, preview, and explicit attachment state.
- `[x]` **Media context service** —Create a backend service that normalizes image inputs, applies safe resizing/encoding, and converts them into the Ollama message format expected by native vision-capable models.
- `[x]` **Chat integration** —Extend `POST /api/chat` so image attachments become first-class chat context instead of ad hoc prompt text.
- `[x]` **Failure behavior** —If the selected model does not support vision, return a clear, sanitized error and keep the text-only chat path intact.
- `[x]` **Frontend experience** —Add image attachment UX with preview, removal, and user-facing capability hints.
- `[x]` **Vision tests and ops limits** —Cover supported and unsupported image requests at the API boundary, and document image timeout/size/format limits in OPERATIONS before enabling the UI entry points.

### 14.6 RAG-3 — quality layer — **complete**

- `[x]` **Optional reranker** —Add reranking behind a dedicated service boundary rather than folding it into basic retrieval logic.
- `[x]` **Optional query rewrite** —Add query rewriting only after retrieval metrics show it solves a measurable failure pattern (conservative whitespace normalization; opt-in via `retrieval_profile=rag3_quality`).
- `[x]` **Retrieval evaluation** —Create a small evaluation set and regression process for retrieval precision, citation correctness, and no-hit behavior.
- `[x]` **Quality gate before claims** —Do not describe the system as "RAG-ready" in README or PROJECT_STATUS until retrieval quality thresholds are documented and regression-tested.

### 14.7 RAG quality closure (post-14.6) — **complete**

**Goal:** Turn RAG-3 **building blocks** into a **closed operational loop**: regression signal, tunable thresholds, and documented ownership — without requiring Postgres or per-user AuthZ.

Aligned with the RAG subsection in [Current reality and improvement map](#current-reality-and-improvement-map).

| Track | Status | Exit |
|-------|--------|------|
| **Regression gate** | `[x]` | `python -m tools.run_rag_eval` runs in **CI** (`.github/workflows/ci.yml` backend job); failure blocks merge. |
| **Thresholds** | `[x]` | RAG knobs and no-hit behavior documented in [OPERATIONS.md](OPERATIONS.md) **RAG retrieval quality**; [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md) §12 points to OPERATIONS + evaldata. |
| **Golden set** | `[x]` | [evaldata/README.md](../evaldata/README.md) + `evaldata/VERSION`; linked from [README.md](../README.md) and this roadmap. |
| **Observability** | `[x]` | `knowledge_retrieval_requests_total{retrieval_profile,outcome}` and `knowledge_query_rewrite_applied_total{retrieval_profile}` on `GET /api/system/metrics`. |

**Dependencies:** §15.3 integration fixtures are available; use them when tightening retrieval beyond pure mocks.

**Explicit non-goals for 14.7:** Replace SQLite or `simple_local_v1` with Postgres/pgvector (that remains a **Decision Log** + capacity trigger, not part of 14.7).

---

## Phase 15: Industrial 9/10 —Priority 2 (Semantics, Then Structure)

**Target release band:** **v1.6+** (may overlap **late v1.5.x** for low-risk doc-only items)  
**Goal:** **Semantic convergence first, directory migration second**—policies and invariants stabilize meaning before `application/` vs `domain/` vs `infra/` reshaping. Phase 15 **consumes** the Phase 13 §13.0 **error model** (stable `code`, `request_id`, handlers); it **does not redefine** that contract—only uses it for policies, tests, and optional tracing.

**Context:** [Current reality and improvement map](#current-reality-and-improvement-map) ties shared-key trust, single-instance storage, RAG loop, tests, deploy constraints, and Phase 15 slices.

**Ordering principle (industrial default):** policy objects + invariants = **narrow, testable moves**; package reshuffle = **wide blast radius**. Do the former first. **§14.7** is complete; proceed with Phase **15** when ready—large AuthZ or datastore changes remain **Decision Log** items.

### 15.1 Domain semantics and policy objects (before big split) — **complete**

- `[x]` **`docs/DOMAIN.md`** —Ubiquitous language for sessions, file context, charts, safeguards; PR checklist in [`.github/pull_request_template.md`](../.github/pull_request_template.md).
- `[x]` **`SafeguardPolicy`** —`backend.domain.safeguard_policy` (`RuleBasedSafeguardPolicy`); `RuleBasedSafeguardService` adapts `ChatMessage` lists; unit tests in `__tests__/test_domain_phase15.py` + existing safeguard tests.
- `[x]` **Chart provenance** —`backend.domain.chart_types`, `chart_provenance_policy` (native tool dataframe + persist `none`→`uploaded` upgrade); `import-linter` layer **`backend.domain`** under **`backend.services`**.
- `[x]` **Invariants** —`chart_spec_requires_version_field` in `build_session_payload`; tests in `__tests__/test_domain_phase15.py`.

### 15.2 Large structural migration (after §15.1) — **initial slice complete**

- `[x]` **Application / domain / infrastructure layout** —`backend/application/` now owns history, knowledge, media, models, system, upload/analyze, chat preflight, and code-sandbox gating; **`import-linter`** layer updated; **reuse** `backend/domain/` (15.1 policies). **Exit met:** [DEPENDENCY_GRAPH.md](DEPENDENCY_GRAPH.md) (current vs target); no new business rules in `routers/`. *Follow-up:* keep migrating any remaining helper logic behind `application/` iteratively.
- `[x]` **Session schema contract** —[SESSION_SCHEMA.md](SESSION_SCHEMA.md) documents `SESSION_PAYLOAD_VERSION`, versioned dict vs legacy list, bump rules. **Exit met:** [test_fake_session_repository.py](../__tests__/test_fake_session_repository.py) in-memory `SessionRepository` round-trip (no SQLite file).
- `[x]` **Ports list** —[PORTS.md](PORTS.md) + link from [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md) §1.9; lists `SessionRepository`, `ConversationLogger`, `TitleGenerator`, `LLMClient`, `Settings`, `SafeguardService`, `TabularContextExtractor`, and stable shared exceptions so routers/application import from one contract face.

### 15.3 Testability — **complete** (narrow scope per plan)

- `[x]` **Clock / random injection** —`goat_ai/clocks.py`: `Clock` protocol, `SystemClock`, `FakeClock`; **`SQLiteIdempotencyStore`** accepts injectable clock; tests avoid `time.sleep` for TTL/expiry. *Deferred:* chat, rate limit, title paths.
- `[x]` **Single primary test entry** —README + [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md) §3.1: **`pytest`** canonical; `unittest discover` legacy/optional. CI unchanged (`python -m pytest __tests__/`).
- `[x]` **Integration tier** —`__tests__/integration/conftest.py` + `test_app_smoke.py` (`/api/health`, `/api/ready` with Ollama skipped); pytest marker `integration`; ~30s budget documented.

### 15.4 Data (deep)

- `[x]` **Message store normalization** —`session_messages` (append-only); dual-read + dual-write with legacy JSON. **Exit:** [SESSION_MESSAGES_MIGRATION.md](SESSION_MESSAGES_MIGRATION.md) + [integration test](../__tests__/integration/test_session_messages_dual_read.py).

### 15.5 Security (deeper)

- `[x]` **AuthZ roadmap + enforcement** —Scoped read/write keys (`GOAT_API_KEY` / `GOAT_API_KEY_WRITE`); session ownership via `X-GOAT-Owner-Id` + `GOAT_REQUIRE_SESSION_OWNER`; service-layer checks on history. **Exit:** [test_api_authz.py](../__tests__/test_api_authz.py). Decision Log: 2026-04-08.
- `[x]` **Secrets hygiene automation** —Informational Gitleaks job in CI (`continue-on-error`); [CONTRIBUTING.md](../CONTRIBUTING.md) + `.env.example` pointers.

### 15.6 Observability (optional stretch)

- `[x]` **Distributed tracing** —`goat_ai/otel_tracing.py`: W3C `traceparent` middleware + spans around Ollama HTTP; default-off (`GOAT_OTEL_ENABLED=0`). **Exit:** [OPERATIONS.md](OPERATIONS.md) OpenTelemetry section.

### 15.7 Phase 15 — execution defaults and assumptions

- **Defaults:** one coordinated refactor window for package layout (not perpetual split); observability-first; AuthZ minimal at service layer; OpenTelemetry optional and default-off.
- **Assumptions:** vision remains **images only** (`png` / `jpeg` / `webp`); media stays on local disk under `GOAT_DATA_DIR`; **Ollama** remains the inference backend; rerank/rewrite stay pluggable with lightweight local implementations first; tracing must not be a hard startup dependency when disabled.

---

## Appendix: RAG subsystem (architecture snapshot)

This replaces the retired long-form `docs/RAG_ARCHITECTURE.md` (historical draft). Current behavior:

- **API family:** RAG is a **separate** contract under `/api/knowledge/*` (uploads, ingestions, search, answers). Chat consumes knowledge via explicit `knowledge_document_ids`; do not treat legacy `/api/upload` as a hidden indexer.
- **Storage:** SQLite metadata + normalized files under `GOAT_DATA_DIR`; vector index backend **`simple_local_v1`** (JSON artifacts per document under the knowledge vector directory).
- **Retrieval quality (RAG-3):** optional **lexical rerank** and **conservative query rewrite** via `retrieval_profile` (`default`, `rag3_lexical`, `rag3_quality`); regression checks in `tools/run_rag_eval.py` / `evaldata/`.
- **Detail:** endpoint tables and behavior — [API_REFERENCE.md](API_REFERENCE.md); machine contract — [openapi.json](openapi.json).

---

## Infrastructure Notes

| Item | Current | Target |
|------|---------|--------|
| Server OS | Linux typical (example: Ubuntu 24.04 + A100) | per operator |
| Public URL | Example: `https://ai.simonbb.com/mingzhi/` | per deployment |
| Port | 62606 (nginx proxy) | 62606 |
| Process mgmt | `nohup` + PID file default on no-root hosts (required fallback); **not** platform-orchestrated (K8s-style) | Try `systemd --user` when D-Bus/session is available; **always** retain nohup/watchdog path for SSH/JupyterHub hosts where user systemd fails; see [§6](#6-deployment--shared-host-not-a-platform-runtime) in [Current reality and improvement map](#current-reality-and-improvement-map) |
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
| 2026-04-07 | Process mgmt: systemd is additive, not a drop-in for nohup | Shared host may lack reliable `systemctl --user`; deploy contract keeps nohup + PID as permanent fallback per [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md) / [OPERATIONS.md](OPERATIONS.md) |
| 2026-04-07 | Phase 11 closed in v1.3.0 | `ChatStreamService` + orchestration split; tabular/title injection; log_service adapter-only guard; wire constants centralized; 79 unittest + 13 black-box OK |
| 2026-04-07 | Phases 13-14 split from prior monolithic Phase 13 | **13** = priority 1; **14** = priority 2 (semantics before package reshuffle). |
| 2026-04-07 | Phase 13 sequencing tightened | **§13.0** = migrations-as-artifacts + error model/registry **before** Wave A. **Wave A** = only four ops items (structured logs+`request_id`, metrics, **liveness**/**readiness**, persistence signals). **Ollama retry/circuit breaker** deferred to **Wave B** after Wave A. **Phase 15** = policy objects + invariants **before** `application/`/`domain/` split; **consumes** §13.0 error model, **does not redefine** it. |
| 2026-04-08 | Phase 13.5 closed | `pip-audit` added to CI, `ruff check` added to CI, changed-file `ruff format` gate added, `docs/SECURITY.md` published, and known vulnerable dependency pins updated (`requests`, `python-multipart`). |
| 2026-04-08 | Phase 13.6-13.8 closed | Graceful shutdown is now documented and implemented in deploy scripts; rollback has an explicit ref-aware runbook; Phase 13 risk triggers are documented in OPERATIONS. |
| 2026-04-08 | RAG classified as a future subsystem, not current baseline capability | Current `/api/upload` remains file-context parsing for prompt injection; roadmap now distinguishes that from true RAG requirements such as chunking, embeddings, vector retrieval, reranking, and retrieval contracts. |
| 2026-04-08 | RAG elevated ahead of multimodal expansion; original Phase 14 moved to Phase 15 | Priority order is now **Phase 13 closeout -> RAG-0 -> RAG-1 -> RAG-2 -> Vision MVP -> RAG-3**. Video implementation was removed from the roadmap because target model support is too inconsistent for the near-term plan. |
| 2026-04-08 | RAG-0 completed; first RAG-1/2 slice landed with a local persistent backend | Knowledge APIs now persist uploads, normalize and chunk narrow document types, write to SQLite metadata tables plus a local `simple_local_v1` vector index, and expose search/answer endpoints with black-box coverage. |
| 2026-04-08 | CSV/XLSX upload path moved fully onto the RAG pipeline; PDF/DOCX joined RAG normalization | `/api/upload` and `/api/upload/analyze` now perform real ingestion and return knowledge identifiers, `/api/chat` can answer with `knowledge_document_ids`, and `pdf/docx` normalize alongside `csv/xlsx/txt/md` in the first RAG ingestion slice. |
| 2026-04-08 | ROADMAP: completed Phases 13 and RAG-0–2 summarized in tables; next work Vision MVP → RAG-3 → Phase 15 | Reduce bullet duplication; roadmap is the single program index. |
| 2026-04-08 | Phase 14.5 Vision MVP and 14.6 RAG-3 closed on main | Vision path shipped; RAG-3 adds rerank/rewrite protocols, `rag3_*` retrieval profiles, `tools/run_rag_eval.py` + `evaldata/` gate documented in README/PROJECT_STATUS. |
| 2026-04-08 | Engineering standards: single canonical doc | Full rules live in `docs/ENGINEERING_STANDARDS.md`; `AGENTS.md` is a short index. `docs/PLAN.md` retired; content folded into this roadmap. `docs/RAG_ARCHITECTURE.md` retired; RAG snapshot lives in ROADMAP appendix. |
| 2026-04-08 | Docs: multi-environment portability | README/OPERATIONS/ENGINEERING_STANDARDS clarify the repo is not limited to one school host; optional high-risk features (e.g. code sandbox) are policy-gated per **ENGINEERING_STANDARDS §15**. |
| 2026-04-08 | ROADMAP: current reality map + §14.7 | Added **Current reality and improvement map** (shared API key, SQLite/local vector, RAG loop, tests, domain semantics, shared-host process model) with **Summary** table; added **§14.7 RAG quality closure** (CI eval, thresholds, golden-set process, observability); **Next** program order is **0 = §14.7**, **1 = Phase 15**. |
| 2026-04-08 | Phase 14.7 implemented | CI runs `python -m tools.run_rag_eval`; `evaldata/README.md` + `VERSION`; OPERATIONS **RAG retrieval quality**; Prometheus `knowledge_retrieval_requests_total` / `knowledge_query_rewrite_applied_total`; ENGINEERING_STANDARDS §12 RAG bullet. |
| 2026-04-08 | Phase 15.4–15.6 (session_messages + AuthZ + optional OTel) | `session_messages` dual-read/write + `sessions.owner_id`; read/write API keys + optional `X-GOAT-Owner-Id`; lazy OpenTelemetry with `traceparent` propagation and Ollama spans; HTTP 403 envelopes preserve explicit `code` when handlers pass `build_error_body`. |
| 2026-04-08 | Developer CLI: `python -m tools.*` | `tools/` is a package (`tools/__init__.py`); run modules from repo root instead of `PYTHONPATH=.` in `.env`. CI uses `python -m tools.run_rag_eval` and `python -m tools.check_api_contract_sync`. |
