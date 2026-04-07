# GOAT AI Project Status

Last updated: 2026-04-07

## What is shipped

- React SPA + FastAPI backend, deployed behind school nginx at `https://ai.simonbb.com/mingzhi/`
- Production bind target `:62606`, with runtime-target introspection at `GET /api/system/runtime-target`
- Ollama-backed chat via `POST /api/chat`
- CSV/XLSX analysis via:
  - `POST /api/upload` as SSE
  - `POST /api/upload/analyze` as JSON
- Session history via `GET /api/history`, `GET /api/history/{id}`, `DELETE /api/history`, `DELETE /api/history/{id}`
- GPU telemetry and rolling inference latency APIs (including first-token latency telemetry)
- Latency telemetry includes p50/p95 and model-scoped buckets for completion and first-token metrics
- Model capability detection via `GET /api/models/capabilities`
- Native chart-tool path: charts are emitted only from real Ollama tool calls, never pre-rendered before the LLM responds
- Typed SSE protocol: `token`, `chart_spec`, `error`, `done`
- Black-box API contract coverage through `__tests__/test_api_blackbox_contract.py`
- Lightweight safeguard layer for clearly unsafe sexual or violent misuse requests in chat
- Single-port runtime-target policy (`:62606`) across deploy scripts and runtime-target API
- Post-deploy contract verification script integrated into Linux and Windows deploy flows
- Model capability probing includes in-process TTL caching

## Current API surface

| Method | Path |
|--------|------|
| GET | `/api/health` |
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
- History reads are normalized at the backend boundary: `/api/history/{id}` returns standard chat roles plus structured `chart_spec` / `file_context`, while legacy stored payloads remain readable through a dedicated compatibility codec
- When `GOAT_API_KEY` is configured, every API except `/api/health` requires `X-GOAT-API-Key`

## Operational notes

- Shared host constraints still apply: no root, no nginx reloads, and `systemctl --user` may be unavailable
- `deploy.sh` defaults to deploying the current checkout; `SYNC_GIT=1` is opt-in
- Preferred GPU is the A100 via `GOAT_GPU_UUID=GPU-fb2cf8f7-e9bf-f136-a3bb-e150426598e8`

## Recommended reference docs

- [OPERATIONS.md](OPERATIONS.md)
- [API_REFERENCE.md](API_REFERENCE.md)
- [ROADMAP.md](ROADMAP.md)
- [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md)
