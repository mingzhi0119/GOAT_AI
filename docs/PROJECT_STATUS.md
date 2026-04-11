# GOAT AI Project Status

Last updated: 2026-04-11

## Release snapshot

- **Current release:** `v1.2.0`
- **Shipped baseline:** phases 11-15 are complete and documented
- **Current planning horizon:** deeper workbench/runtime completion, sandbox follow-ons, desktop distribution maturity, and P2 operating-model hardening

## Shipped platform summary

### Core app

- React SPA + FastAPI backend
- Ollama-backed chat with typed SSE events: `thinking`, `token`, `chart_spec`, `artifact`, `error`, `done`
- split liveness/readiness probes at `GET /api/health` and `GET /api/ready`
- Prometheus metrics at `GET /api/system/metrics`
- stable JSON error envelope using `detail`, `code`, and `request_id`

### Knowledge and media

- persisted upload and ingestion pipeline for `csv`, `xlsx`, `txt`, `md`, `pdf`, and `docx`
- retrieval-backed chat and `/api/knowledge/*` contract family
- local `simple_local_v1` vector index with optional lexical rerank and conservative query rewrite
- image uploads for vision-capable chat via `POST /api/media/uploads`
- RAG quality regression runner in CI via `python -m tools.run_rag_eval`

### Sessions, artifacts, and authorization

- persisted session history with `session_messages` normalization and legacy compatibility
- generated chat artifacts served from persisted artifact ids
- credential-backed authorization context with tenant/principal scoping
- explicit persisted-resource ownership envelopes at storage boundaries
- capability gates that distinguish policy denial from runtime unavailability

### Workbench and sandbox

- durable workbench tasks with polling and event timelines
- minimal runtime execution for `plan`, `browse`, and `deep_research`
- declarative workbench source registry with `knowledge` ready and `web` still runtime-incomplete
- durable code sandbox execution with persisted events and replayable logs
- Docker-first isolation with `localhost` as an explicit trusted-dev fallback

### Desktop

- Tauri 2 desktop shell
- PyInstaller-built backend sidecar
- working Windows packaging flow producing `.msi` and NSIS installers
- desktop smoke coverage for sidecar boot and startup diagnostics

### Governance and operations

- staged release governance workflow and approval gate
- versioned observability assets in-repo
- nightly performance smoke with explicit budgets
- backup, restore, rollback, and recovery-drill coverage
- CI gates for lint, tests, build, contract sync, dependency audit, secret scan, and desktop supply chain

## Current known boundaries

- `canvas` remains in the public task enum but is not implemented yet
- workbench `web` retrieval is still declared before it is truly runtime-ready
- project memory and connectors are not implemented yet
- storage remains SQLite-first and single-writer by design
- future storage-shape changes require a new migration/compatibility/rollback decision log
- Windows desktop packaging is ahead of macOS/Linux packaged validation and signing

## Status by active roadmap area

- **16B storage evolution:** complete; repository ownership boundaries are explicit across sessions, artifacts, knowledge, media, workbench, and sandbox, and future datastore-shape changes require a separate decision package
- **17 runtime platform:** partial workbench runtime is landed; canvas, real web retrieval, project memory, and connectors remain open
- **18 sandbox follow-ons:** MVP is landed; richer async control, egress policy, and Rust supervisor work remain open
- **19 desktop maturity:** Windows packaging is landed; cross-platform packaged validation, signing, updater readiness, and deeper native runtime operations remain open
- **engineering quality uplift:** P0 and P1 are complete; P2 operating-model work remains

## Recommended live references

- [ROADMAP.md](ROADMAP.md)
- [OPERATIONS.md](OPERATIONS.md)
- [API_REFERENCE.md](API_REFERENCE.md)
- [API_ERRORS.md](API_ERRORS.md)
- [SECURITY.md](SECURITY.md)
- [BACKUP_RESTORE.md](BACKUP_RESTORE.md)
- [ROLLBACK.md](ROLLBACK.md)
- [RELEASE_GOVERNANCE.md](RELEASE_GOVERNANCE.md)
- [AGENTS.md](../AGENTS.md)
