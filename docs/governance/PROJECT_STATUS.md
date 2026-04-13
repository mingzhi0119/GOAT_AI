# GOAT AI Project Status

Last updated: 2026-04-13

## Release snapshot

- **Current release:** `v1.2.0`
- **Shipped baseline:** phases 11-15 are complete and documented

## Shipped platform summary

### Core app

- React SPA + FastAPI backend
- Ollama-backed chat with typed SSE events: `thinking`, `token`, `chart_spec`, `artifact`, `error`, `done`
- split liveness/readiness probes at `GET /api/health` and `GET /api/ready`
- Prometheus metrics at `GET /api/system/metrics`
- stable JSON error envelope using `detail`, `code`, and `request_id`

### Knowledge and media

- persisted upload and ingestion pipeline for `csv`, `xlsx`, `txt`, `md`, `pdf`, and `docx`
- knowledge source files, normalized text/metadata, and vector-index payloads now persist through a storage-key/object-store boundary instead of direct path assumptions
- retrieval-backed chat and `/api/knowledge/*` contract family
- local `simple_local_v1` vector index with optional lexical rerank and conservative query rewrite
- image uploads for vision-capable chat via `POST /api/media/uploads`
- RAG quality regression runner in CI via `python -m tools.quality.run_rag_eval`

### Sessions, artifacts, and authorization

- persisted session history with `session_messages` normalization and legacy compatibility
- generated chat artifacts served from persisted artifact ids while keeping `download_url` on the stable `/api/artifacts/{artifact_id}` contract
- generated artifacts, media attachments, and future workspace-export blobs now resolve through the configured object store (`local` by default, `s3` optional)
- credential-backed authorization context with tenant/principal scoping
- explicit persisted-resource ownership envelopes at storage boundaries
- capability gates that distinguish policy denial from runtime unavailability

### Workbench and sandbox

- durable workbench tasks with polling and event timelines
- minimal runtime execution for `plan`, `browse`, `deep_research`, and `canvas`
- typed durable workspace outputs, with `canvas_document` as the first shipped output kind
- session-bound workspace outputs now restore through history reads, outputs can be reopened directly by durable id, and outputs can be exported into downloadable artifacts
- declarative workbench source registry with `knowledge` ready and experimental DDGS-backed `web` retrieval now runtime-ready
- bounded LangGraph-backed multi-step research for `browse` and `deep_research`, with durable plan/retrieval/follow-up/synthesis events and a private rollback switch to the legacy single-pass path
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
- repo-native decision records now have a canonical entrypoint under `docs/decisions/`, approved templates, and PR guidance for tradeoffs, rollback posture, and proof links
- the engineering standards and PR template now include an explicit admission gate for future workbench, connector, and project-memory expansion, including feature-spec, decision-package, caller-scoped contract-proof, runtime-parser, and docs-sync requirements
- frontend-only `dependency-cruiser` now runs in standard CI beside lint/build/contract gates to pin module direction, cycle checks, and API-layer import boundaries
- frontend runtime schema parsing now covers the current shipped JSON adapters under `frontend/src/api/` plus the current chat/upload/code-sandbox SSE boundaries, while the existing `docs/api/openapi.json -> openapi-typescript -> contract:check` chain remains the only generated contract source
- lightweight feature-scoped `spec/plan/tasks` artifacts now exist under `docs/governance/specs/` as a non-canonical pilot for complex brownfield changes
- versioned observability assets in-repo
- nightly performance smoke with explicit budgets
- merge-blocking PR latency gate for the core in-process chat path
- weekly quality snapshot workflow for recurring coverage, security-review, and optional performance-summary capture
- recurring fault-injection workflow for upstream-unavailable, persistence-failure, database recovery-drill, artifact rollback drill, and desktop-boot diagnostics
- recurring installed Windows drill in `.github/workflows/fault-injection.yml` so installer regressions are not release-only discoveries
- backup, restore, rollback, and recovery-drill coverage
- documented vulnerability response, dependency-refresh cadence, and credential-rotation policy
- CI gates for lint, tests, build, contract sync, dependency audit, secret scan, and desktop supply chain
- `desktop-package-windows` now has desktop-change trigger boundaries, merge-blocking packaged-shell fault smoke, retained build/smoke diagnostics, and governance tests so missing-sidecar, early-exit, and pre-ready-timeout regressions stay auditable for desktop-related changes
- `.github/workflows/desktop-provenance.yml` and `.github/workflows/fault-injection.yml` now always retain structured MSI/NSIS install -> healthy launch -> pre-ready fault -> uninstall evidence, plus workflow metadata and step summaries for failure diagnosis
- caller-scoped workbench feature semantics and observability asset coverage are now mechanically pinned by contract tests, workflow tests, and docs/runbook truth instead of roadmap watchpoints

## Current known boundaries

- workbench browse/deep-research now use a bounded multi-step LangGraph loop rather than the earlier single-pass evidence brief, but the runtime is still intentionally step-limited instead of open-ended autonomous research
- project memory and connectors are not implemented yet
- future workbench, connector, and project-memory widening is now governed by the admission gate in `docs/standards/ENGINEERING_STANDARDS.md` rather than by roadmap notes alone
- runtime metadata now supports an opt-in hosted/server Postgres backend with Alembic-owned schema truth and deterministic SQLite snapshot import/parity tooling, while local and desktop remain SQLite-first by design
- Windows desktop packaging, signing, and provenance are ahead of macOS/Linux public packaged validation
- pre-ready desktop restart/backoff is shipped, and the packaged-shell fault smoke in `desktop-package-windows` is now path-scoped, merge-blocking, and retention-backed for desktop-related changes
- installed Windows startup evidence now stays auditable across release and scheduled workflows: signed installer validation lives in `.github/workflows/desktop-provenance.yml`, recurring installer drift detection lives in `.github/workflows/fault-injection.yml`, and both retain structured failure artifacts even when the drill fails
- GitHub-side branch protection wiring, signing-secret availability, and hosted Windows runner behavior remain external conditions outside repo-only proof
- frontend runtime schema parsing now covers the current shipped frontend API adapters, but future workbench/frontier surfaces should adopt the same pattern only when a real frontend consumer lands
- `docs/governance/specs/` is intentionally a narrow working-artifact pilot, not a second governance source

## Shipped coverage by roadmap area

- **16B/16C storage evolution:** complete; repository ownership boundaries are explicit across sessions, artifacts, knowledge, media, workbench, and sandbox, persisted blobs now use `storage_key` plus the local/S3 object-store boundary
- **16D Postgres-backed runtime persistence:** complete for the hosted/server opt-in path; Alembic owns the Postgres runtime schema, repository adapters preserve the existing contracts, and SQLite snapshot export/import/parity plus rollback runbooks now anchor cutover proof
- **17 runtime platform:** the shipped baseline includes durable workbench tasks, canvas/workspace-output persistence, session restoration, direct output reopen, output-to-artifact export linkage, experimental DDGS-backed public-web retrieval, and bounded LangGraph-backed multi-step research for browse/deep-research
- **18 sandbox follow-ons:** the shipped baseline includes the Docker-first sandbox MVP, queued-only async control-plane behavior, durable execution/event storage, and replayable sandbox logs
- **19 desktop maturity:** the shipped baseline includes signed Windows packaging, packaged-desktop validation, installed Windows evidence retention, and pre-ready startup fault handling
- **governance tooling follow-ons:** decision records and PR guidance are landed, frontend-only `dependency-cruiser` is merge-blocking, current shipped frontend API adapters now validate JSON and current SSE boundaries through shared runtime parsers, and lightweight feature specs are available as a non-canonical pilot for complex brownfield changes
- **engineering quality uplift:** audit remediation through the 2026-04-12 P3 governance-maintenance closeout is complete inside the repository, and the current industrial-score floor is backed by mechanical gates, workflow evidence, and contract tests

## Recommended live references

- [ROADMAP.md](ROADMAP.md)
- [ROADMAP_ARCHIVE.md](ROADMAP_ARCHIVE.md)
- [OPERATIONS.md](../operations/OPERATIONS.md)
- [OBJECT_STORAGE_CONTRACT.md](../architecture/OBJECT_STORAGE_CONTRACT.md)
- [API_REFERENCE.md](../api/API_REFERENCE.md)
- [API_ERRORS.md](../api/API_ERRORS.md)
- [SECURITY.md](SECURITY.md)
- [BACKUP_RESTORE.md](../operations/BACKUP_RESTORE.md)
- [ROLLBACK.md](../operations/ROLLBACK.md)
- [RELEASE_GOVERNANCE.md](../operations/RELEASE_GOVERNANCE.md)
- [AGENTS.md](../../AGENTS.md)
