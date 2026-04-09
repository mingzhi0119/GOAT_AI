# GOAT AI Roadmap

> Last updated: 2026-04-09 - **v1.0.0** tags Phase **11-12**; **main** additionally ships **Phase 13**, **Phase 14** (through **14.7**), and **all of Phase 15** through **15.11**. **Next:** execute Phase **16C** before **16A** and **16B**.
> Current release tag: **v1.0.0**
> Compact snapshot: [PROJECT_STATUS.md](PROJECT_STATUS.md) - Engineering standards: [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md)

---

## Shipped (v1.0.0)

| Phase | Content |
|-------|---------|
| 0–10 | Environment setup, FastAPI backend, React frontend, production deploy, product polish, reliability/UX, conversation history, quality/observability, charting/telemetry, access/security, native chart-tool path |
| 11 | **Industrialization and decoupling:** `ChatStreamService` owns SSE/tool/safeguard streaming; `chat_orchestration.py` holds `PromptComposer` / `ChartToolOrchestrator` / `SessionPersistenceService`; `chat_service.py` is a thin entry; injectable `TabularContextExtractor` + `LLMClient`; `log_service` import confined to adapters; wire markers centralized; `test_architecture_boundaries` added |
| 12 | **Hardening and scale-readiness:** explicit chart data-source policy, architecture guardrails, latency p50/p95 with model buckets, expanded `/api/chat` black-box matrix, deploy post-check script, API contract CI sync gate, model capability TTL cache |

---

## Archived: Phase 13 — Run, Observe, Recover (complete)

Phase 13 delivered the full operations baseline for a shared-host, single-instance deployment. Numbered SQL migrations and a `schema_migrations` checksum table replaced ad hoc schema changes. A stable JSON error envelope (`detail`, `code`, `request_id`) was introduced with consistent exception handlers and `X-Request-ID` propagation. The observability stack grew to include structured logging, Prometheus-style counters and latency histograms (`http_requests_total`, `chat_stream_completed_total`, `ollama_errors_total`, `sqlite_log_write_failures_total`), and a liveness/readiness split at `GET /api/health` and `GET /api/ready`. Ollama resilience was hardened with retry/backoff/jitter and a lightweight circuit breaker on idempotent reads, alongside optional `Idempotency-Key` support for upload-analyze and chat session-append paths. SLO tables, a load-smoke CLI (`python -m tools.load_chat_smoke`), and chat hot-path size guardrails (`422` on overflow) completed the observability tier. Session schema gained `schema_version` and `updated_at` audit fields. CI was extended with `pip-audit` and `ruff check`. Graceful shutdown and a ref-aware rollback runbook were added to the deploy scripts. All Phase 13 risk triggers are documented in [OPERATIONS.md](OPERATIONS.md).

---

## Archived: Phase 14 — RAG-first Capability Expansion (complete)

Phase 14 built the full knowledge pipeline and vision capability from scratch. RAG-0 established the `/api/knowledge/*` contract family (uploads, ingestions, search, answers) as a first-class API surface separate from legacy `/api/upload`. RAG-1 added persistent file storage under `GOAT_DATA_DIR`, migration `007`, normalization and chunking of `csv`, `xlsx`, `txt`, `md`, `pdf`, and `docx`, a local `simple_local_v1` vector index, and ingestion status tracking. RAG-2 wired retrieval-backed generation into `POST /api/chat` via explicit `knowledge_document_ids`, including no-hit fallback behavior. The Vision MVP (14.5) introduced `POST /api/media/uploads` for `png`, `jpeg`, and `webp` images, model capability probing to distinguish vision from text-only models, and `image_attachment_ids` on chat — with a clean error path when the selected model does not support vision. RAG-3 (14.6) added optional lexical reranking and conservative query rewriting behind a `retrieval_profile` parameter (`default`, `rag3_lexical`, `rag3_quality`), implemented as injectable `Protocol` seams so implementations are swappable. Section 14.7 closed the quality loop: `python -m tools.run_rag_eval` runs on every CI backend build against `evaldata/rag_eval_cases.jsonl`; Prometheus exposes `knowledge_retrieval_requests_total{retrieval_profile,outcome}` and `knowledge_query_rewrite_applied_total{retrieval_profile}`; retrieval knobs and no-hit behavior are documented in [OPERATIONS.md](OPERATIONS.md); the golden-set process lives in [evaldata/README.md](../evaldata/README.md).

---

## Archived: Phase 15.1–15.6 — Semantics, Then Structure (complete)

Phase 15 worked from domain meaning outward to package layout. Section 15.1 produced [DOMAIN.md](DOMAIN.md) as the ubiquitous-language reference for sessions, file context, charts, and safeguards, and introduced typed policy objects: `SafeguardPolicy` / `RuleBasedSafeguardPolicy` in `backend.domain`, chart provenance helpers, and a `chart_spec_requires_version_field` invariant in `build_session_payload`. Section 15.2 executed the structural migration: `backend/application/` now owns history, knowledge, media, models, system, upload/analyze, chat preflight, and code-sandbox gating; `backend/application/ports` is the shared contract face for `Settings`, Protocols, and stable exception re-exports; `import-linter` layer rules were updated; [DEPENDENCY_GRAPH.md](DEPENDENCY_GRAPH.md) and [SESSION_SCHEMA.md](SESSION_SCHEMA.md) document the current and target wiring. Section 15.3 introduced the `Clock` Protocol (`goat_ai/clocks.py`) with injectable `SystemClock` and `FakeClock`, wired it into `SQLiteIdempotencyStore` for TTL expiry without `time.sleep`, established pytest as the canonical test runner, and added an `__tests__/integration/` tier with a smoke test covering `/api/health` and `/api/ready`. Section 15.4 normalized session messages into an append-only `session_messages` table with dual-read/write compatibility against the legacy JSON blob, documented in [SESSION_MESSAGES_MIGRATION.md](SESSION_MESSAGES_MIGRATION.md). Section 15.5 introduced scoped API keys (`GOAT_API_KEY` / `GOAT_API_KEY_WRITE`), optional session ownership via `X-GOAT-Owner-Id` and `GOAT_REQUIRE_SESSION_OWNER`, service-layer enforcement, and a Gitleaks informational CI job. Section 15.6 added lazy OpenTelemetry tracing (`goat_ai/otel_tracing.py`) with W3C `traceparent` middleware and Ollama HTTP spans, default-off via `GOAT_OTEL_ENABLED=0`, documented in [OPERATIONS.md](OPERATIONS.md).

### 15.7 Phase 15 — execution defaults and assumptions

- **Defaults:** one coordinated refactor window for package layout (not perpetual split); observability-first; AuthZ minimal at service layer; OpenTelemetry optional and default-off.
- **Assumptions:** vision remains **images only** (`png` / `jpeg` / `webp`); media stays on local disk under `GOAT_DATA_DIR`; **Ollama** remains the inference backend; rerank/rewrite stay pluggable with lightweight local implementations first; tracing must not be a hard startup dependency when disabled.

---

## Archived: Phase 15.8-15.11 - closeout slices (complete)

Phase 15 is now fully complete on main. Sections 15.8-15.11 are retained here as the final closeout record before Phase 16 planning begins.

These slices address deferred items from 15.2 and 15.3 and extend the domain and test foundations laid in 15.1 and 15.3. They are lower blast-radius than the structural migration and can proceed independently.

### 15.8 Clock injection — completion (deferred from 15.3)

**Goal:** eliminate the remaining `time.time()` / `datetime.now()` call-sites that affect testable behavior in the chat, rate-limit, and title-generation paths; replace them with injected `Clock` so unit tests need no `time.sleep`.

**Current status (2026-04-09):** complete. The rate-limit path is wired to `Clock` through the policy/store split and covered by `__tests__/test_rate_limit_clock.py`, and the title/session-persist path now accepts injected `Clock` with deterministic coverage in `__tests__/test_chat_service.py`.

| Task | Exit criterion |
|------|----------------|
| Inject `Clock` into the rate-limiter (HTTP middleware or service) | Rate-limit window expiry controlled by `FakeClock` in unit tests; no `time.sleep` in those tests |
| Inject `Clock` into the title-generation path | Title TTL / staleness logic testable with `FakeClock` |
| (Optional) `Random` Protocol for any nonce or sampling code | Seeded fake passes deterministic tests |
| Update `__tests__/` for affected paths | All new tests use `FakeClock`; CI green |

**Non-goals:** changing the chat streaming protocol or SSE framing.

### 15.9 Application layer audit (follow-up from 15.2)

**Goal:** ensure no residual business logic lives in `backend/routers/` or is split across `backend/services/` in a way that violates the `application → services → domain` import order.

**Current status (2026-04-09):** complete. The history delete path was moved into `backend.application.history.delete_history_session`, and the broader router/application audit is now closed across history, knowledge, upload, chat, system, models, media, artifacts, and code-sandbox routes. [DEPENDENCY_GRAPH.md](DEPENDENCY_GRAPH.md) reflects the audited wiring.

| Task | Exit criterion |
|------|----------------|
| Audit `backend/routers/` for inline orchestration or domain decisions | Any found logic moved to `backend/application/`; routers become thin validate-call-return shells |
| Audit `backend/services/` for rules that belong in `backend/domain/` | Policy or invariant helpers promoted; services remain orchestrators |
| `import-linter` clean run with no exceptions or `# noqa` bypasses | CI `lint-imports` job green |
| Update [DEPENDENCY_GRAPH.md](DEPENDENCY_GRAPH.md) to reflect final wiring | Diagram matches actual import graph |

**Non-goals:** moving `goat_ai/` internals or changing the public API surface.

### 15.10 Integration test expansion (follow-up from 15.3)

**Goal:** extend `__tests__/integration/` beyond the health/readiness smoke test to cover the three highest-value end-to-end flows, using real SQLite + temp `GOAT_DATA_DIR` but mocking Ollama at the `LLMClient` Protocol boundary.

**Current status (2026-04-09):** complete. `__tests__/integration/test_session_history.py`, `__tests__/integration/test_knowledge_flow.py`, and `__tests__/integration/test_chat_with_knowledge.py` now cover the session-history flow, knowledge upload→ingest→search flow, `/api/knowledge/answers` semantic contract, and retrieval-backed chat prompt injection.

| Flow | Exit criterion |
|------|----------------|
| Knowledge pipeline: upload → ingest → search round-trip | `test_knowledge_flow.py` passes with temp dir; checks `document_id` returned and vector index populated |
| Chat with `knowledge_document_ids`: retrieval-backed generation | `test_chat_with_knowledge.py` passes; verifies retrieved context injected into prompt and LLM synthesis instruction present |
| Session history round-trip: write → read → delete | `test_session_history.py` covers `GET /api/history/{id}`, message normalization, and `DELETE` |
| `POST /api/knowledge/answers` semantic contract | Test confirms current snippet-dump behavior; output makes the chat-vs-answers semantic divergence visible so the product decision (keep as-is vs. add LLM synthesis) can be made with evidence |
| Total integration tier stays under 60 s CI budget | Documented in [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md) Section 3.1 |

**Non-goals:** end-to-end tests against a live Ollama instance (those remain out of CI scope).

### 15.11 Domain model hardening (follow-up from 15.1)

**Goal:** promote the two most rule-heavy cross-cutting concerns — rate limiting and session schema validation — into typed domain objects, and expand `DOMAIN.md` to cover them.

**Current status (2026-04-09):** complete. `backend.domain.rate_limit_policy` now exposes `RateLimitSubject`, `RateLimitPolicy`, and `RateLimitDecision`; HTTP security delegates to a policy/store pair; [DOMAIN.md](DOMAIN.md) has the new terms; and `decode_session_payload` now raises `SessionSchemaError` for unsupported future payload versions while preserving legacy compatibility.

| Task | Exit criterion |
|------|----------------|
| `RateLimitSubject` / `RateLimitPolicy` in `backend.domain`: encapsulate bucket identity, window size, limit, and key derivation | Unit-tested in `test_domain_rate_limit_policy.py` and `test_domain_phase15.py`; middleware delegates to policy + store |
| Session read invariant: validate `schema_version` on decode, not only on write | `decode_session_payload` raises a typed `SessionSchemaError` on unknown version; covered in `test_fake_session_repository.py` |
| `DOMAIN.md` updated with rate-limit and session-version terms | PR checklist link active; no new ubiquitous terms undocumented |
| `import-linter` layer for `backend.domain` unchanged (no new upward imports) | CI green |

**Non-goals:** full RBAC, per-user rate buckets, or Postgres-backed session store (all Decision Log items).

---

## Next implementation direction

| Order | Focus | Notes |
|-------|--------|--------|
| **0** | **Phase 16C: credential-backed authorization context and tenancy envelope** | Stabilize `principal / tenant / scope / authorization decision` on top of shared API keys before any broader Phase 16 work |
| **1** | **Phase 16A: production-safe capability gates** | Build future capability gates on top of the 16C authz context rather than a raw shared key |
| **2** | **Phase 16B: storage evolution** | Revisit datastore changes only after authz and resource boundaries are explicit |

> **Known semantic divergence (tracked):** `POST /api/knowledge/answers` still returns a raw snippet-dump (`"Relevant retrieved context:\n" + bullets`, `snippet[:220]`) with no LLM in the loop. The chat path (`POST /api/chat` with `knowledge_document_ids`) sends the same retrieved context to the model with an explicit "synthesize rather than dumping snippets" instruction. These two endpoints now have different answer semantics for the same underlying retrieval. The 15.10 integration tests will make this divergence explicit; resolution (whether to add LLM synthesis to `/answers` or document the difference as intentional) is a product decision to be made at that point.

### Phase 16C decision log and execution checklist

**Decision:** Phase 16C introduces credential-backed authorization and tenancy boundaries, not end-user identity.

**Status:** complete  
**Sequence:** `16C -> 16A -> 16B`

- [x] Re-sequence Phase 16 so authz context lands before capability gates and datastore expansion.
- [x] Keep `GOAT_API_KEY`, `GOAT_API_KEY_WRITE`, and `X-GOAT-Owner-Id` ingress compatibility.
- [x] Introduce typed `PrincipalId`, `TenantId`, `Scope`, `AuthorizationDecision`, and `AuthorizationContext`.
- [x] Add a minimal credential registry with env fallback for existing shared-key deployments.
- [x] Bind `AuthorizationContext` in HTTP middleware and expose it through a dependency.
- [x] Move resource-level authorization into `backend.services.authorizer` (invoked from application use cases and services) instead of routers/middleware.
- [x] Add structured allow/deny authz audit events with stable identifiers only.
- [x] Add `tenant_id` / `principal_id` columns for sessions and chat artifacts using additive migrations.
- [x] Extend the same tenancy envelope to knowledge documents and media uploads.
- [x] Close out docs and operations guidance for multi-credential configuration and rollout.
- [x] Mark Phase 16C complete only after the broader resource adoption and regression matrix are green.

### Near-term execution order (project-calibrated)

| Horizon | Focus |
|---------|--------|
| **v1.0.x** | Ops hardening carry-overs: SQLite backup thresholds, security audit as exposure grows |
| **v1.1.x** | Phase 16C implementation slices: authz context, tenancy envelope, and resource adoption |
| **v1.2+** | Phase 16A capability gates, then Phase 16B storage evolution; each remains a Decision Log item before any code lands |

---

## Current reality and improvement map

This section records **constraints that match today's shipped architecture** and **where planned improvements sit** in this roadmap. It does not replace exit criteria in individual phases.

### 1. Access control — shared API key (no per-user AuthN/AuthZ)

| Reality (main) | Improvement path | Roadmap / docs home |
|----------------|------------------|---------------------|
| Protection is **`GOAT_API_KEY` + `X-GOAT-API-Key`** when set; optional **`GOAT_API_KEY_WRITE`** splits read vs write HTTP methods; optional **`X-GOAT-Owner-Id`** + **`GOAT_REQUIRE_SESSION_OWNER`** scopes sessions (not end-user AuthN). | Document threat model, rotation, and blast radius; keep rate limits and health exceptions as today. | [SECURITY.md](SECURITY.md), [OPERATIONS.md](OPERATIONS.md); Phase **15.5** enforcement complete. |
| Feature gates expose **`policy_allowed: null`** until richer AuthZ exists; runtime gating (503) is separate from policy (403). | Scoped keys + owner header are opt-in via env; **not** full IAM until product requires it. | [test_api_authz.py](../__tests__/test_api_authz.py); [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md) Section 15. |
| Per-user sessions in SQLite are **not** authenticated identities; `owner_id` is a **convenience partition**, not proof of principal. | Phase **16C** adds credential-backed authorization and tenancy boundaries without claiming end-user identity. | [SESSION_MESSAGES_MIGRATION.md](SESSION_MESSAGES_MIGRATION.md); Decision Log 2026-04-08 and 2026-04-09. |

**Priority:** Docs + operational discipline **first**; code changes for multi-key **only** when exposure grows.

### 2. Data plane — SQLite + local vector index (`simple_local_v1`)

| Reality (main) | Improvement path | Roadmap / docs home |
|----------------|------------------|---------------------|
| **Single primary SQLite** for app metadata; **files + JSON vector artifacts** under `GOAT_DATA_DIR`; not a multi-writer cluster store. | Treat **one active writer** as the supported deployment; document backup/restore and migration discipline. | [OPERATIONS.md](OPERATIONS.md), [BACKUP_RESTORE.md](BACKUP_RESTORE.md); Phase **13** Wave B "multi-instance limitations". |
| Horizontal scale-out **not** a current goal; multiple Uvicorn workers or multiple hosts require a **Decision Log** + storage change. | **If** capacity forces it: Postgres (or equivalent) + optional external vector store — **after** ops stability gates. | Phase **13** non-goals; new Decision Log entry before any migration. |

**Priority:** Correct **single-instance** ops and backups **before** distributed data stores.

### 3. RAG quality — eval gate closed; ongoing maintenance

| Reality (main) | Improvement path | Roadmap / docs home |
|----------------|------------------|---------------------|
| **Section 14.7** delivered CI eval, thresholds in OPERATIONS, golden-set process, and Prometheus observability. | Iterate eval cases as retrieval behavior evolves; keep `run_rag_eval` green on every backend build. | [evaldata/README.md](../evaldata/README.md); [OPERATIONS.md](OPERATIONS.md) **RAG retrieval quality**. |
| Further tuning (score cutoffs, dashboards) | Optional; not blocking Phase 15 remaining work. | Phase **16** scope if needed. |

**Priority:** Keep the CI gate green; add eval cases when retrieval changes.

### 4. Testing — black-box strong; integration tier expanding

| Reality (main) | Improvement path | Roadmap / docs home |
|----------------|------------------|---------------------|
| Contract tests and architecture guards exist; integration tier now covers health/readiness smoke, session history, knowledge upload→ingest→search, and retrieval-backed chat. | Maintain coverage and CI runtime budget as retrieval behavior evolves. | Section **15.10**; [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md) testing rules. |
| Clock is injected into idempotency, rate-limit, and title/session-persist paths. | Keep new time-based behavior testable through `Clock` rather than wall-clock sleeps. | Section **15.8**. |

**Priority:** **High** leverage — lowers cost of Phase 16 and any retrieval changes.

### 5. Domain semantics — policies and invariants present; rate-limit and session-read not yet formalized

| Reality (main) | Improvement path | Roadmap / docs home |
|----------------|------------------|---------------------|
| `SafeguardPolicy`, chart provenance policy, `chart_spec_requires_version_field`, and `RateLimitSubject` / `RateLimitPolicy` exist in `backend.domain`; `RateLimitStore` lives in services; future session payload versions now fail loudly on read. | Maintain the invariant when evolving session schema. | Section **15.11**; [DOMAIN.md](DOMAIN.md). |
| Application layer migration is complete and router boundaries have been audited. | Maintain the import direction and keep new business rules in `application` or `domain`, not routers. | Section **15.9**. |

**Priority:** Before any Phase 16 AuthZ or datastore expansion.

### 6. Deployment — shared host, not a platform runtime

| Reality (main) | Improvement path | Roadmap / docs home |
|----------------|------------------|---------------------|
| No root; **`nohup` + PID** is the permanent fallback; `systemd --user` when it works. Process lifecycle is **ops scripts**, not Kubernetes-style orchestration. | Harden **deploy**, **readiness**, **graceful shutdown**, log rotation; document failure modes; avoid assuming `systemctl` in SSH sessions. | [OPERATIONS.md](OPERATIONS.md) **Deployment profiles**; Phase **13.6** complete; Decision Log **2026-04-07**. |
| "Platform-grade" self-healing is **out of scope** unless hosting changes. | Revisit only if deployment environment changes. | Decision Log; not Phase 15 default. |

**Priority:** **Reliability of the current path** over new orchestration layers.

### Summary — where work lands

| Theme | Primary roadmap anchor |
|-------|-------------------------|
| Shared key + future minimal AuthZ | Section 15.5 (done); Phase 16 for full IAM |
| Single-instance SQLite + local vector | OPERATIONS, Phase 13 risk triggers; Postgres = Decision Log |
| RAG eval + thresholds + CI | Section 14.7 (done — maintain green) |
| Clock injection (chat/rate-limit/title) | Closed in **Section 15.8** |
| Application layer audit | Closed in **Section 15.9** |
| Integration test expansion | Closed in **Section 15.10** |
| Domain invariants (rate-limit policy, session read) | Closed in **Section 15.11** |
| Deploy / process lifecycle | OPERATIONS, Phase 13 closed |

---

## Appendix: RAG subsystem (architecture snapshot)

Current behavior:

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
| Process mgmt | `nohup` + PID file default on no-root hosts (required fallback); **not** platform-orchestrated (K8s-style) | Try `systemd --user` when D-Bus/session is available; **always** retain nohup/watchdog path for SSH/JupyterHub hosts where user systemd fails |
| Log files | `logs/fastapi.log` + user-space rotation script | same |
| Node version | 24.14.1 (`.nvmrc`) | 24.x |
| Python (reference prod) | 3.12.6 | 3.12.x until host upgrade |
| Python (CI + dev for OpenAPI parity) | 3.14.x | 3.14.x (keep in sync with `.github/workflows/ci.yml`) |

---

## Decision Log

| Date | Decision | Reason |
|------|----------|--------|
| 2026-03-30 | Use port 62606 instead of 8002 in production | Only 62606 is reachable through school nginx |
| 2026-03-30 | Vite `base: './'` | Required for JupyterHub proxy and nginx sub-path compatibility |
| 2026-03-30 | SSE over WebSocket | Simpler and more proxy-friendly; native browser support |
| 2026-03-30 | No React Router | Single-page app; extra routing complexity had little benefit |
| 2026-03-31 | Dual-port deploy reverted | Production uses `:62606` only |
| 2026-04-07 | Process mgmt: systemd is additive, not a drop-in for nohup | Shared host may lack reliable `systemctl --user`; deploy contract keeps nohup + PID as permanent fallback |
| 2026-04-07 | Phase 11 closed in v1.0.0 | `ChatStreamService` + orchestration split; tabular/title injection; log_service adapter-only guard; wire constants centralized; 79 unittest + 13 black-box passed |
| 2026-04-07 | Phases 13–14 split from prior monolithic Phase 13 | **13** = priority 1 (ops); **14** = priority 2 (RAG/vision). |
| 2026-04-07 | Phase 13 sequencing tightened | Section 13.0 = migrations + error model before Wave A; Wave A = four ops items; Ollama retry/circuit breaker deferred to Wave B; Phase 15 = policy objects + invariants before package split. |
| 2026-04-08 | Phase 13.5 closed | `pip-audit` + `ruff check` in CI; `docs/SECURITY.md` published; vulnerable dependency pins updated. |
| 2026-04-09 | CI / dev Python 3.14 for OpenAPI parity | Backend CI uses Python **3.14**; regenerate `docs/openapi.json` with the same interpreter as CI. |
| 2026-04-08 | Phase 13.6–13.8 closed | Graceful shutdown documented and implemented; rollback runbook added; Phase 13 risk triggers in OPERATIONS. |
| 2026-04-08 | RAG classified as a future subsystem, not current baseline | `/api/upload` remains file-context parsing; roadmap distinguishes it from true RAG (chunking, embeddings, vector retrieval, reranking). |
| 2026-04-08 | RAG elevated ahead of multimodal expansion; original Phase 14 moved to Phase 15 | Priority: Phase 13 closeout → RAG-0 → RAG-1 → RAG-2 → Vision MVP → RAG-3. Video removed from roadmap. |
| 2026-04-08 | RAG-0 completed; first RAG-1/2 slice landed with a local persistent backend | Knowledge APIs persist uploads, normalize and chunk documents, write to SQLite + `simple_local_v1` vector index, expose search/answer endpoints. |
| 2026-04-08 | CSV/XLSX upload path moved onto RAG pipeline; PDF/DOCX joined RAG normalization | `/api/upload` and `/api/upload/analyze` perform real ingestion; chat supports `knowledge_document_ids`. |
| 2026-04-08 | Phase 14.5 Vision MVP and 14.6 RAG-3 closed on main | Vision path shipped; RAG-3 adds rerank/rewrite protocols, `rag3_*` retrieval profiles, `tools/run_rag_eval.py` + `evaldata/` gate. |
| 2026-04-08 | Engineering standards: single canonical doc | Full rules live in `docs/ENGINEERING_STANDARDS.md`; `AGENTS.md` is a short index. `docs/PLAN.md` retired; `docs/RAG_ARCHITECTURE.md` retired — RAG snapshot lives in ROADMAP appendix. |
| 2026-04-08 | Docs: multi-environment portability | README/OPERATIONS/ENGINEERING_STANDARDS clarify the repo is not limited to one school host; optional high-risk features are policy-gated per ENGINEERING_STANDARDS Section 15. |
| 2026-04-08 | Phase 14.7 implemented | CI runs `python -m tools.run_rag_eval`; `evaldata/README.md` + `VERSION`; OPERATIONS RAG retrieval quality; Prometheus `knowledge_retrieval_requests_total` / `knowledge_query_rewrite_applied_total`; ENGINEERING_STANDARDS Section 12 RAG bullet. |
| 2026-04-08 | Phase 15.4–15.6 complete | `session_messages` dual-read/write + `sessions.owner_id`; read/write API keys + optional `X-GOAT-Owner-Id`; lazy OpenTelemetry with `traceparent` and Ollama spans. |
| 2026-04-08 | Developer CLI: `python -m tools.*` | `tools/` is a package (`tools/__init__.py`); run modules from repo root. CI uses `python -m tools.run_rag_eval` and `python -m tools.check_api_contract_sync`. |
| 2026-04-09 | Phase 15.8, 15.10, and 15.11 closed on main | 15.8: `Clock` now reaches rate-limit and title/session-persist flows. 15.10: integration coverage includes retrieval-backed chat in addition to history and knowledge-pipeline flows. 15.11: domain rate-limit policy/store split is landed and future-version session payloads now raise `SessionSchemaError` on read. |
| 2026-04-09 | Phase 15.9 closed; Phase 15 fully complete on main | Router/application boundaries audited across history, knowledge, upload, chat, system, models, media, artifacts, and code-sandbox routes; `lint-imports` kept green; dependency graph docs updated. |
