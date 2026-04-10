# GOAT AI Project Status

Last updated: 2026-04-10

## Release

- **Current release:** `v1.2.0`
- **Shipped release milestone:** Phases 11-15 are complete and documented; Phase 16 sequencing is next.
- **Main-branch status:** Phase 13 closeout work is landed across migrations, error semantics, readiness/liveness split, metrics, idempotency, rollback/backup runbooks, and CI hardening. See [ROADMAP.md](ROADMAP.md).
- **Phase 14 status:** RAG-0 through **RAG-3** are complete on main: persisted uploads, SQLite metadata, local `simple_local_v1` vector index, retrieval-backed chat, optional **lexical rerank** and **conservative query rewrite** via `retrieval_profile` (`default` / `rag3_lexical` / `rag3_quality`), plus `python -m tools.run_rag_eval` over `evaldata/rag_eval_cases.jsonl`. **Vision MVP** (`POST /api/media/uploads`, `image_attachment_ids` on chat when the model reports vision) is landed.
- **Phase 14.7 (RAG quality closure):** CI runs `python -m tools.run_rag_eval` on every backend pipeline; `GOAT_RAG_RERANK_MODE` and `retrieval_profile` are documented in [OPERATIONS.md](OPERATIONS.md); golden-set process in [evaldata/README.md](../evaldata/README.md); Prometheus exposes `knowledge_retrieval_requests_total` and `knowledge_query_rewrite_applied_total` at `GET /api/system/metrics`.
- **Phase 15.1 (domain semantics):** [DOMAIN.md](DOMAIN.md) defines ubiquitous language; `backend.domain` holds safeguard policy, chart provenance helpers, and chart-spec version invariant; [.github/pull_request_template.md](../.github/pull_request_template.md) links DOMAIN + contract regen.
- **Phase 15 structural closeout:** `backend.application` now owns history, knowledge, media, models, system, upload/analyze, chat preflight, and code-sandbox gating so routers stay thin while public API shapes remain unchanged; `backend.application.ports` is the shared contract face for `Settings`, Protocols, and stable exception re-exports.
- **Phase 15.4-15.6:** `session_messages` table (dual-read/write with legacy JSON blob); optional `sessions.owner_id`; read/write API keys and optional `X-GOAT-Owner-Id` for session scoping; lazy OpenTelemetry (`GOAT_OTEL_ENABLED`) with `traceparent` middleware and Ollama spans. See [SESSION_MESSAGES_MIGRATION.md](SESSION_MESSAGES_MIGRATION.md), [OPERATIONS.md](OPERATIONS.md), [test_api_authz.py](../__tests__/test_api_authz.py).
- **Phase 15.8 status:** complete. `Clock` is injected into `register_http_security`, and the title/session-persist path now accepts injected `Clock` as well; tests cover deterministic timestamps without wall-clock sleeps.
- **Phase 15.9 status:** complete. Router/application boundary audit is closed: history, knowledge, upload, chat, system, models, media, artifacts, and code-sandbox routes are thin adapters over `backend.application`, and [DEPENDENCY_GRAPH.md](DEPENDENCY_GRAPH.md) reflects the audited wiring.
- **Phase 15.10 status:** complete. Integration tests now cover session history round-trips (`test_session_history.py`), knowledge upload→ingest→search and `/api/knowledge/answers` contract (`test_knowledge_flow.py`), plus retrieval-backed chat prompt injection and persistence (`test_chat_with_knowledge.py`).
- **Phase 15.11 status:** complete. `RateLimitSubject`, `RateLimitDecision`, and `RateLimitPolicy` now live in `backend.domain.rate_limit_policy`, `backend.http_security` delegates rate limiting through a policy/store pair, [DOMAIN.md](DOMAIN.md) documents the terms, and `decode_session_payload` now raises `SessionSchemaError` for unsupported future payload versions while preserving older payload compatibility.
- **Phase 15 overall:** complete on main. Remaining roadmap work is now Phase 16 planning and decision-log sequencing.
- **Frontend shell status:** composer control-surface polish, responsive `wide/narrow` chat-shell baseline, and the integrated manual UI verification workflow are landed on `main`.
- **Frontend appearance status:** a Codex-like appearance system is landed on `main`: dedicated Appearance panel, `light/dark/system` mode, `classic/urochester/thu` styles, accent color, UI/code font selection, contrast tuning, translucent sidebar control, root-token theming, local preference persistence, style-specific footer logos, denser sidebar history layout, and theme-card alignment polish. Architecture hand-off: [APPEARANCE.md](APPEARANCE.md).
- **Phase 16A status:** complete. `code_sandbox` now enforces separate policy and runtime gates on top of request-scoped `AuthorizationContext`: `GET /api/system/features` returns caller-specific `policy_allowed`, `POST /api/code-sandbox/exec` returns **503** + `FEATURE_UNAVAILABLE` for runtime denial and **403** + `FEATURE_DISABLED` for policy denial (`sandbox:execute`), and Prometheus exposes `feature_gate_denials_total{feature,gate_kind,reason}`.
- **RAG-ready wording:** use the term **RAG-ready** in release notes or marketing only after `python -m tools.run_rag_eval` passes in CI or pre-release checks and this file still documents the same threshold.

## What is shipped

- React SPA + FastAPI backend; reference deployment behind nginx at `https://ai.simonbb.com/mingzhi/` (the codebase targets multiple environments; see README **Environments**)
- Production bind target `:62606`, with runtime-target introspection at `GET /api/system/runtime-target`
- Split health model with liveness at `GET /api/health` and readiness at `GET /api/ready`
- Prometheus-style metrics at `GET /api/system/metrics`
- Ollama-backed chat via `POST /api/chat`
- Knowledge-file ingestion via:
  - `POST /api/upload` as SSE
  - `POST /api/upload/analyze` as JSON
- Contract-first knowledge API skeleton via:
  - `POST /api/knowledge/uploads`
  - `GET /api/knowledge/uploads/{document_id}`
  - `POST /api/knowledge/ingestions`
  - `GET /api/knowledge/ingestions/{ingestion_id}`
  - `POST /api/knowledge/search`
  - `POST /api/knowledge/answers`
- Session history via `GET /api/history`, `GET /api/history/{id}`, `DELETE /api/history`, `DELETE /api/history/{id}`
- GPU telemetry and rolling inference latency APIs, including first-token latency telemetry
- Latency telemetry includes p50/p95 and model-scoped buckets for completion and first-token metrics
- Model capability detection via `GET /api/models/capabilities`
- Native chart-tool path: charts are emitted only from real Ollama tool calls, never pre-rendered before the LLM responds
- Vision images: `POST /api/media/uploads` stores PNG/JPEG/WebP for use with `image_attachment_ids` on `POST /api/chat` when the selected model reports vision capability
- Typed SSE protocol: `thinking`, `token`, `chart_spec`, `artifact`, `error`, `done`
- Black-box API contract coverage through `__tests__/test_api_blackbox_contract.py`
- Architecture guard suite (`__tests__/test_architecture_boundaries.py`) included in standard `unittest discover` runs
- Lightweight safeguard layer for clearly unsafe sexual or violent misuse requests in chat
- Single-port runtime-target policy (`:62606`) across deploy scripts and runtime-target API
- Post-deploy contract verification script integrated into Linux and Windows deploy flows
- Model capability probing includes in-process TTL caching
- Stable JSON error envelope now uses `detail`, `code`, and `request_id` across exception handlers and protected middleware paths
- Knowledge uploads now persist to `GOAT_DATA_DIR`, normalize `csv`, `xlsx`, `txt`, `md`, `pdf`, and `docx`, and write retrieval metadata into SQLite plus a local `simple_local_v1` vector index
- Ollama idempotent-read resilience: retry with backoff+jitter and circuit-breaker states for `/api/tags` and `/api/show`
- Optional `Idempotency-Key` support for `POST /api/upload/analyze` and chat session append path (`POST /api/chat` with `session_id`)
- SQLite-backed idempotency TTL table for duplicate request replay and write dedupe
- Capacity guardrails on `POST /api/chat` enforce max message count and max payload size (`422` on overflow)
- Load smoke utility (`python -m tools.load_chat_smoke`) provides one-command p50/p95 validation against chat SSE plus optional `/api/system/inference` snapshot
- Session history contract includes `schema_version` audit field; `updated_at` remains part of list/detail APIs
- SQLite backup/restore runbook published at [BACKUP_RESTORE.md](BACKUP_RESTORE.md) and linked from OPERATIONS
- Security/tooling baseline includes [SECURITY.md](SECURITY.md), `ruff check` in CI, `pip-audit` in CI, and changed-file `ruff format` gating for Python edits
- Operations baseline includes graceful shutdown, ref-aware rollback via `deploy.sh` / `deploy.ps1`, and documented Phase 13 risk triggers in OPERATIONS
- Codex-like frontend appearance system with a dedicated settings panel, named styles, root-applied theme tokens, startup anti-flicker hydration, and local appearance persistence
- Sidebar history optimistic insertion now makes the active conversation appear immediately before the post-stream refresh lands
- UI hides Thinking disclosures unless the message was sent with thinking enabled, even if the backend stream still includes reasoning events

## Current API surface

| Method | Path |
|--------|------|
| GET | `/api/health` |
| GET | `/api/ready` |
| GET | `/api/system/metrics` |
| GET | `/api/models` |
| GET | `/api/models/capabilities` |
| POST | `/api/chat` |
| POST | `/api/upload` |
| POST | `/api/upload/analyze` |
| POST | `/api/knowledge/uploads` |
| GET | `/api/knowledge/uploads/{document_id}` |
| POST | `/api/knowledge/ingestions` |
| GET | `/api/knowledge/ingestions/{ingestion_id}` |
| POST | `/api/knowledge/search` |
| POST | `/api/knowledge/answers` |
| POST | `/api/media/uploads` |
| GET | `/api/history` |
| GET | `/api/history/{session_id}` |
| DELETE | `/api/history` |
| DELETE | `/api/history/{session_id}` |
| GET | `/api/system/gpu` |
| GET | `/api/system/inference` |
| GET | `/api/system/runtime-target` |
| GET | `/api/system/features` |
| POST | `/api/code-sandbox/exec` |

## Important behavior notes

- `/api/chat` streams typed JSON SSE objects, not legacy string sentinels (`thinking` and `token` are distinct streams for reasoning vs answer text)
- `/api/upload` now emits `knowledge_ready` then `done`; it ingests the file into the knowledge subsystem instead of returning prompt-injection `file_context`
- `/api/upload/analyze` now returns `document_id`, `ingestion_id`, `status`, and `retrieval_mode`; `chart: null` remains only for backward compatibility
- `/api/chat` accepts `knowledge_document_ids` and uses retrieval-backed generation when indexed documents are attached
- Chat can emit persisted downloadable artifacts over SSE and serve them from `GET /api/artifacts/{artifact_id}`
- `/api/knowledge/*` routes now support persisted upload, synchronous ingestion, retrieval, retrieval-backed answers, and attached-document fallback when lexical retrieval misses
- `/api/health` is liveness only; `/api/ready` is the deploy/readiness probe and returns `503` when SQLite or the optional Ollama probe is not ready
- History reads are normalized at the backend boundary: `/api/history/{id}` returns standard chat roles plus structured `chart_spec`, legacy `file_context`, and `knowledge_documents`, while legacy stored payloads remain readable through a dedicated compatibility codec
- When `GOAT_API_KEY` is configured, every API except `/api/health` and `/api/ready` requires `X-GOAT-API-Key`

## Operational notes

- Shared host constraints still apply: no root, no nginx reloads, and `systemctl --user` may be unavailable
- `deploy.sh` defaults to deploying the current checkout; `SYNC_GIT=1` is opt-in
- Preferred GPU is the A100 via `GOAT_GPU_UUID=GPU-fb2cf8f7-e9bf-f136-a3bb-e150426598e8`

## Recommended reference docs

- [AGENTS.md](../AGENTS.md) (short index) - [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md) (canonical rules)
- [OPERATIONS.md](OPERATIONS.md)
- [API_REFERENCE.md](API_REFERENCE.md)
- [API_ERRORS.md](API_ERRORS.md)
- [BACKUP_RESTORE.md](BACKUP_RESTORE.md)
- [ROLLBACK.md](ROLLBACK.md)
- [SECURITY.md](SECURITY.md)
- [ROADMAP.md](ROADMAP.md)
