# GOAT AI Project Status

Last updated: 2026-04-08

## Release

- **Current release:** `v1.3.0`
- **Shipped release milestone:** Phase 11 (industrialization / decoupling) is complete.
- **Main-branch status:** Phase 13 closeout work is landed across migrations, error semantics, readiness/liveness split, metrics, idempotency, rollback/backup runbooks, and CI hardening. See [ROADMAP.md](ROADMAP.md).

## What is shipped

- React SPA + FastAPI backend, deployed behind school nginx at `https://ai.simonbb.com/mingzhi/`
- Production bind target `:62606`, with runtime-target introspection at `GET /api/system/runtime-target`
- Split health model with liveness at `GET /api/health` and readiness at `GET /api/ready`
- Prometheus-style metrics at `GET /api/system/metrics`
- Ollama-backed chat via `POST /api/chat`
- CSV/XLSX analysis via:
  - `POST /api/upload` as SSE
  - `POST /api/upload/analyze` as JSON
- Session history via `GET /api/history`, `GET /api/history/{id}`, `DELETE /api/history`, `DELETE /api/history/{id}`
- GPU telemetry and rolling inference latency APIs, including first-token latency telemetry
- Latency telemetry includes p50/p95 and model-scoped buckets for completion and first-token metrics
- Model capability detection via `GET /api/models/capabilities`
- Native chart-tool path: charts are emitted only from real Ollama tool calls, never pre-rendered before the LLM responds
- Typed SSE protocol: `token`, `chart_spec`, `error`, `done`
- Black-box API contract coverage through `__tests__/test_api_blackbox_contract.py`
- Architecture guard suite (`__tests__/test_architecture_boundaries.py`) included in standard `unittest discover` runs
- Lightweight safeguard layer for clearly unsafe sexual or violent misuse requests in chat
- Single-port runtime-target policy (`:62606`) across deploy scripts and runtime-target API
- Post-deploy contract verification script integrated into Linux and Windows deploy flows
- Model capability probing includes in-process TTL caching
- Stable JSON error envelope now uses `detail`, `code`, and `request_id` across exception handlers and protected middleware paths
- Ollama idempotent-read resilience: retry with backoff+jitter and circuit-breaker states for `/api/tags` and `/api/show`
- Optional `Idempotency-Key` support for `POST /api/upload/analyze` and chat session append path (`POST /api/chat` with `session_id`)
- SQLite-backed idempotency TTL table for duplicate request replay and write dedupe
- Capacity guardrails on `POST /api/chat` enforce max message count and max payload size (`422` on overflow)
- Load smoke utility `tools/load_chat_smoke.py` provides one-command p50/p95 validation against chat SSE plus optional `/api/system/inference` snapshot
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
| GET | `/api/history` |
| GET | `/api/history/{session_id}` |
| DELETE | `/api/history` |
| DELETE | `/api/history/{session_id}` |
| GET | `/api/system/gpu` |
| GET | `/api/system/inference` |
| GET | `/api/system/runtime-target` |

## Important behavior notes

- `/api/chat` streams typed JSON SSE objects, not legacy string sentinels
- `/api/upload` emits `file_context` then `done`; it no longer emits starter charts
- `/api/upload/analyze` keeps `chart: null` only for backward compatibility
- `/api/health` is liveness only; `/api/ready` is the deploy/readiness probe and returns `503` when SQLite or the optional Ollama probe is not ready
- History reads are normalized at the backend boundary: `/api/history/{id}` returns standard chat roles plus structured `chart_spec` / `file_context`, while legacy stored payloads remain readable through a dedicated compatibility codec
- When `GOAT_API_KEY` is configured, every API except `/api/health` and `/api/ready` requires `X-GOAT-API-Key`

## Operational notes

- Shared host constraints still apply: no root, no nginx reloads, and `systemctl --user` may be unavailable
- `deploy.sh` defaults to deploying the current checkout; `SYNC_GIT=1` is opt-in
- Preferred GPU is the A100 via `GOAT_GPU_UUID=GPU-fb2cf8f7-e9bf-f136-a3bb-e150426598e8`

## Recommended reference docs

- [OPERATIONS.md](OPERATIONS.md)
- [API_REFERENCE.md](API_REFERENCE.md)
- [API_ERRORS.md](API_ERRORS.md)
- [BACKUP_RESTORE.md](BACKUP_RESTORE.md)
- [ROLLBACK.md](ROLLBACK.md)
- [SECURITY.md](SECURITY.md)
- [ROADMAP.md](ROADMAP.md)
- [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md)
