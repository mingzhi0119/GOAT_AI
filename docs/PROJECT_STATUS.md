# GOAT AI Project Status

Last updated: 2026-04-09

## Release

- **Current release:** `v1.3.0`
- **Shipped release milestone:** Phase 11 (industrialization / decoupling) is complete.
- **Main-branch status:** Phase 13 closeout work is landed across migrations, error semantics, readiness/liveness split, metrics, idempotency, rollback/backup runbooks, and CI hardening. See [ROADMAP.md](ROADMAP.md).
- **Phase 14 status:** RAG-0 through **RAG-3** are complete on main: persisted uploads, SQLite metadata, local `simple_local_v1` vector index, retrieval-backed chat, optional **lexical rerank** and **conservative query rewrite** via `retrieval_profile` (`default` / `rag3_lexical` / `rag3_quality`), plus `python -m tools.run_rag_eval` over `evaldata/rag_eval_cases.jsonl`. **Vision MVP** (`POST /api/media/uploads`, `image_attachment_ids` on chat when the model reports vision) is landed.
- **Phase 14.7 (RAG quality closure):** CI runs `python -m tools.run_rag_eval` on every backend pipeline; `GOAT_RAG_RERANK_MODE` and `retrieval_profile` are documented in [OPERATIONS.md](OPERATIONS.md); golden-set process in [evaldata/README.md](../evaldata/README.md); Prometheus exposes `knowledge_retrieval_requests_total` and `knowledge_query_rewrite_applied_total` at `GET /api/system/metrics`.
- **Phase 15.1 (domain semantics):** [DOMAIN.md](DOMAIN.md) defines ubiquitous language; `backend.domain` holds safeguard policy, chart provenance helpers, and chart-spec version invariant; [.github/pull_request_template.md](../.github/pull_request_template.md) links DOMAIN + contract regen.
- **Phase 15.4–15.6:** `session_messages` table (dual-read/write with legacy JSON blob); optional `sessions.owner_id`; read/write API keys and optional `X-GOAT-Owner-Id` for session scoping; lazy OpenTelemetry (`GOAT_OTEL_ENABLED`) with `traceparent` middleware and Ollama spans. See [SESSION_MESSAGES_MIGRATION.md](SESSION_MESSAGES_MIGRATION.md), [OPERATIONS.md](OPERATIONS.md), [test_api_authz.py](../__tests__/test_api_authz.py).
- **Feature gates (§15):** `GET /api/system/features` exposes a stable `code_sandbox` snapshot (config + Docker probe; `policy_allowed` reserved for future AuthZ). `POST /api/code-sandbox/exec` is a scaffold: **503** + `FEATURE_UNAVAILABLE` when the **runtime** gate is closed; **403** + `FEATURE_DISABLED` reserved for **policy** denial; **501** when the gate passes but execution is not implemented.
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
- Typed SSE protocol: `token`, `chart_spec`, `error`, `done`
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

- `/api/chat` streams typed JSON SSE objects, not legacy string sentinels
- `/api/upload` now emits `knowledge_ready` then `done`; it ingests the file into the knowledge subsystem instead of returning prompt-injection `file_context`
- `/api/upload/analyze` now returns `document_id`, `ingestion_id`, `status`, and `retrieval_mode`; `chart: null` remains only for backward compatibility
- `/api/chat` accepts `knowledge_document_ids` and uses retrieval-backed answering when indexed documents are attached
- `/api/knowledge/*` routes now support persisted upload, synchronous ingestion, retrieval, retrieval-backed answers, and attached-document fallback when lexical retrieval misses
- `/api/health` is liveness only; `/api/ready` is the deploy/readiness probe and returns `503` when SQLite or the optional Ollama probe is not ready
- History reads are normalized at the backend boundary: `/api/history/{id}` returns standard chat roles plus structured `chart_spec`, legacy `file_context`, and `knowledge_documents`, while legacy stored payloads remain readable through a dedicated compatibility codec
- When `GOAT_API_KEY` is configured, every API except `/api/health` and `/api/ready` requires `X-GOAT-API-Key`

## Operational notes

- Shared host constraints still apply: no root, no nginx reloads, and `systemctl --user` may be unavailable
- `deploy.sh` defaults to deploying the current checkout; `SYNC_GIT=1` is opt-in
- Preferred GPU is the A100 via `GOAT_GPU_UUID=GPU-fb2cf8f7-e9bf-f136-a3bb-e150426598e8`

## Recommended reference docs

- [AGENTS.md](../AGENTS.md) (short index) · [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md) (canonical rules)
- [OPERATIONS.md](OPERATIONS.md)
- [API_REFERENCE.md](API_REFERENCE.md)
- [API_ERRORS.md](API_ERRORS.md)
- [BACKUP_RESTORE.md](BACKUP_RESTORE.md)
- [ROLLBACK.md](ROLLBACK.md)
- [SECURITY.md](SECURITY.md)
- [ROADMAP.md](ROADMAP.md)
