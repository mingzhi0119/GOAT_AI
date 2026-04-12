# GOAT AI Project Status

Last updated: 2026-04-12

## Release snapshot

- **Current release:** `v1.2.0`
- **Shipped baseline:** phases 11-15 are complete and documented
- **Current planning horizon:** deeper workbench/runtime completion, sandbox follow-ons, and desktop distribution maturity

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
- RAG quality regression runner in CI via `python -m tools.quality.run_rag_eval`

### Sessions, artifacts, and authorization

- persisted session history with `session_messages` normalization and legacy compatibility
- generated chat artifacts served from persisted artifact ids
- credential-backed authorization context with tenant/principal scoping
- explicit persisted-resource ownership envelopes at storage boundaries
- capability gates that distinguish policy denial from runtime unavailability

### Workbench and sandbox

- durable workbench tasks with polling and event timelines
- minimal runtime execution for `plan`, `browse`, `deep_research`, and `canvas`
- typed durable workspace outputs, with `canvas_document` as the first shipped output kind
- session-bound workspace outputs now restore through history reads, outputs can be reopened directly by durable id, and outputs can be exported into downloadable artifacts
- declarative workbench source registry with `knowledge` ready and experimental DDGS-backed `web` retrieval now runtime-ready
- durable code sandbox execution with persisted events and replayable logs
- Docker-first isolation with `localhost` as an explicit trusted-dev fallback

### Desktop

- Tauri 2 desktop shell
- PyInstaller-built backend sidecar
- working Windows packaging flow producing `.msi` and NSIS installers
- signed Windows desktop release path in `.github/workflows/desktop-provenance.yml`
- desktop smoke coverage for sidecar boot and startup diagnostics
- packaged desktop shell diagnostics persisted under the platform app-log directory
- packaged desktop startup now uses bounded pre-ready restart/backoff before the main window is revealed, then still fails explicitly if the sidecar never becomes ready or exits unexpectedly after reveal
- release governance now retains installed Windows evidence for both MSI and NSIS artifacts before signed installers are uploaded

### Governance and operations

- artifact-first staged release governance workflow and approval gate
- desktop provenance workflow for the Linux sidecar artifact plus signed Windows installer digests/attestations
- merge-blocking backend CI now stages `backend-fast -> backend-heavy -> backend`, so triage clears changed-file Ruff/format blockers before reading deeper backend failures
- versioned observability assets in-repo
- nightly performance smoke with explicit budgets
- merge-blocking PR latency gate for the core in-process chat path
- weekly quality snapshot workflow for recurring coverage, security-review, and optional performance-summary capture
- recurring fault-injection workflow for upstream-unavailable, persistence-failure, database recovery-drill, artifact rollback drill, and desktop-boot diagnostics
- recurring installed Windows drill in `.github/workflows/fault-injection.yml` so installer regressions are not release-only discoveries
- backup, restore, rollback, and recovery-drill coverage
- documented vulnerability response, dependency-refresh cadence, and credential-rotation policy
- CI gates for lint, tests, build, contract sync, dependency audit, secret scan, and desktop supply chain
- `desktop-package-windows` now also carries packaged-shell fault smoke so missing-sidecar, early-exit, and pre-ready-timeout startup regressions stay merge-blocking for desktop-related changes

## Current known boundaries

- workbench public-web retrieval is now a bounded single-pass DDGS-backed evidence brief, not yet a multi-step autonomous research runtime
- project memory and connectors are not implemented yet
- storage remains SQLite-first and single-writer by design
- future storage-shape changes require a new migration/compatibility/rollback decision log
- Windows desktop packaging, signing, and provenance are ahead of macOS/Linux public packaged validation
- pre-ready desktop restart/backoff is shipped, but the packaged-shell fault smoke in `desktop-package-windows` is now the critical evidence path because Rust unit tests alone were not enough to guard fail-closed startup behavior
- installed Windows startup evidence is now split across release and scheduled workflows: signed installer validation lives in `.github/workflows/desktop-provenance.yml`, while recurring installer drift detection lives in `.github/workflows/fault-injection.yml`

## Status by active roadmap area

- **16B storage evolution:** complete; repository ownership boundaries are explicit across sessions, artifacts, knowledge, media, workbench, and sandbox, and future datastore-shape changes require a separate decision package
- **17 runtime platform:** partial workbench runtime is landed; canvas, typed workspace outputs, session restoration, direct output reopen, output-to-artifact export linkage, and experimental DDGS-backed public-web retrieval are now in place, while deeper multi-step research behavior, project memory, and connectors remain open
- **18 sandbox follow-ons:** MVP is landed; richer async control, egress policy, and Rust supervisor work remain open
- **19 desktop maturity:** signed Windows packaging and packaged validation are landed; macOS/Linux public packaged validation, updater readiness, and deeper native runtime operations remain open
- **engineering quality uplift:** audit remediation through P2 is complete; remaining follow-on work is now capability/runtime roadmap scope in [ROADMAP.md](ROADMAP.md)

## Recommended live references

- [ROADMAP.md](ROADMAP.md)
- [OPERATIONS.md](../operations/OPERATIONS.md)
- [API_REFERENCE.md](../api/API_REFERENCE.md)
- [API_ERRORS.md](../api/API_ERRORS.md)
- [SECURITY.md](SECURITY.md)
- [BACKUP_RESTORE.md](../operations/BACKUP_RESTORE.md)
- [ROLLBACK.md](../operations/ROLLBACK.md)
- [RELEASE_GOVERNANCE.md](../operations/RELEASE_GOVERNANCE.md)
- [AGENTS.md](../../AGENTS.md)
