# GOAT AI Project Status

Last updated: 2026-04-14

## Release snapshot

- **Current release:** `v1.3.0`
- **Shipped baseline:** phases 11-15 are complete and documented

## Shipped platform summary

### Core app

- React SPA + FastAPI backend
- public split deployment runs with the frontend on
  `https://goat-dev.vercel.app` and the backend on
  `https://goat-api.duckdns.org`
- Ollama-backed chat with typed SSE events:
  `thinking`, `token`, `chart_spec`, `artifact`, `error`, `done`
- split liveness/readiness probes at `GET /api/health` and `GET /api/ready`
- Prometheus metrics at `GET /api/system/metrics`
- stable JSON error envelope using `detail`, `code`, and `request_id`

### Knowledge, sessions, and artifacts

- persisted upload and ingestion pipeline for supported text/tabular/document
  formats
- retrieval-backed knowledge APIs and chat integration
- persisted session history with legacy compatibility
- generated artifacts served from persisted ids, with the stable
  `/api/artifacts/{artifact_id}` contract
- stable `/api/artifacts/{artifact_id}` contract
- generated blobs resolve through the configured object store boundary
  (`local` by default, `s3` optional)

### Authorization and deployment behavior

- public browser deployments can require one shared site password while still
  isolating history and artifact access per browser session
- account and Google browser login are landed for remote-capable deployments
- public backend model discovery and chat entrypoints enforce a server-side
  allowlist only for the remote/public deployment surface
- three deployment modes are shipped and isolated:
  `local`, `school_server`, and `remote`

### Workbench and sandbox

- durable workbench tasks with polling and event timelines
- bounded runtime execution for `plan`, `browse`, `deep_research`, and `canvas`
- typed durable workspace outputs and output reopen/export linkage
- shared source catalog and capability assembly under existing workbench/system
  wrappers
- durable code sandbox execution with persisted events and replayable logs
- queued plus running sandbox cancellation and fail-closed restart recovery are
  shipped
- Docker-first isolation with `localhost` as an explicit trusted-dev fallback

### Desktop

- Tauri 2 desktop shell
- PyInstaller-built backend sidecar
- working Windows packaging flow producing `.msi` and NSIS installers
- signed Windows desktop release path in
  `.github/workflows/desktop-provenance.yml`
- Linux packaged proof/readiness workflow coverage is landed
- macOS public distribution remains blocked pending signing/notarization work
- packaged startup uses bounded pre-ready restart/backoff
- installed Windows evidence is retained in release and drill workflows
- `desktop-package-windows` keeps merge-blocking packaged-shell fault smoke for
  desktop-related changes

### Governance and operations

- artifact-first staged release governance workflow and approval gate
- backend CI stages `backend-fast -> backend-heavy -> backend`
- contract sync, dependency audit, secret scan, rollback, backup/restore, and
  recovery-drill coverage are documented and gated
- repo-native decision records, ops runbooks, and observability assets are
  checked in
- `desktop-package-windows` remains a named merge-blocking desktop gate
- merge-blocking packaged-shell fault smoke remains part of the desktop gate
- current desktop packaging governance and evidence remain retention-backed and
  auditable
- `OBJECT_STORAGE_CONTRACT.md` is part of the live reference set

## Current known boundaries

- browse/deep-research remains intentionally bounded rather than open-ended
  autonomous runtime behavior
- read-only project memory and static connector bindings are shipped, but
  write-capable connectors and live remote adapters are not
- runtime metadata supports opt-in hosted/server Postgres while local and
  desktop remain SQLite-first
- sandbox retry remains terminal-only and `network_policy` remains
  disabled-only
- signed Windows public packaging is shipped, but public macOS
  signing/notarization and updater activation remain open
- GitHub-side branch protection wiring, signing-secret availability, and hosted
  Windows runner behavior remain external conditions outside repo-only proof
- `docs/governance/specs/` remains a narrow working-artifact pilot rather than
  a second governance source

## Shipped coverage by roadmap area

- **16B/16C storage evolution:** complete; persisted blobs use `storage_key`
  plus the local/S3 object-store boundary
- **16D Postgres-backed runtime persistence:** complete for the hosted/server
  opt-in path
- **17 runtime platform:** durable workbench tasks, bounded browse/deep
  research, read-only `project_memory`, and caller-scoped static connector
  bindings are shipped
- **18 sandbox follow-ons:** the shipped baseline includes the Docker-first
  sandbox MVP, queued/running cancellation, fail-closed restart recovery, and
  replayable sandbox logs
- **19 desktop maturity:** the shipped baseline includes signed Windows
  packaging, Linux packaged proof/readiness, and macOS blocker-report
  scaffolding
- **engineering quality uplift:** the current industrial-score floor is backed
  by mechanical gates, workflow evidence, and contract tests

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
