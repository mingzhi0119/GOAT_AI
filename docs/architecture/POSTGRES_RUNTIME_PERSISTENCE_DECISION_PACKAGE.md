# Postgres Runtime Persistence Decision Package

Last updated: 2026-04-13

## Purpose

This document records the landed **Phase 16D** posture for hosted/server runtime
metadata. The shipped implementation moves the governed runtime-metadata family to an
opt-in Postgres backend for server deployments while preserving the existing
HTTP/API, caller-scoped authz, recovery, and object-store semantics.

## Governed runtime-metadata family

Phase 16D treats the runtime metadata plane as one governed family:

- `conversations`
- `sessions`
- `session_messages`
- `idempotency_keys`
- `chat_artifacts`
- `knowledge_documents`
- `knowledge_ingestions`
- `knowledge_chunks`
- `media_uploads`
- `workbench_tasks`
- `workbench_task_events`
- `workbench_workspace_outputs`
- `code_sandbox_executions`
- `code_sandbox_execution_events`
- `code_sandbox_execution_logs`
- `schema_migrations`

`conversations` remains part of the hosted compatibility surface. It is included in
the Postgres schema, repository adapters, snapshot import/parity tooling, and
rollback proof.

## Landed posture

- `GOAT_RUNTIME_METADATA_BACKEND=sqlite` remains the default runtime metadata mode
- `GOAT_RUNTIME_METADATA_BACKEND=postgres` is a hosted/server-only mode and requires
  `GOAT_DEPLOY_MODE=2` plus `GOAT_RUNTIME_POSTGRES_DSN`
- local development and desktop installs stay on SQLite
- Alembic under `backend/alembic/` owns hosted/server Postgres schema truth
- runtime adapters stay on explicit SQL/query boundaries rather than introducing an
  ORM rewrite
- repository and service callers still bind through the existing runtime-persistence
  factory seam in `backend/services/runtime_persistence.py`
- `storage_key` remains the durable link from runtime metadata rows to Phase 16C
  object-store payloads

## Landed implementation surface

- backend selection and initialization:
  - `goat_ai/config/settings.py`
  - `backend/services/runtime_persistence.py`
  - `backend/services/postgres_runtime_support.py`
- governed inventory and snapshot logic:
  - `backend/services/runtime_metadata_inventory.py`
  - `backend/services/runtime_metadata_snapshot.py`
- hosted/server Postgres repository adapters:
  - `backend/services/chat_runtime.py`
  - `backend/services/idempotency_service.py`
  - `backend/services/knowledge_repository.py`
  - `backend/services/media_service.py`
  - `backend/services/workbench_runtime.py`
  - `backend/services/code_sandbox_runtime.py`
- operator-facing cutover tooling:
  - `python -m tools.ops.upgrade_runtime_postgres_schema`
  - `python -m tools.ops.export_runtime_metadata_snapshot`
  - `python -m tools.ops.import_runtime_metadata_snapshot`
  - `python -m tools.ops.check_runtime_metadata_parity`

## Cutover and rollback posture

The first shipped hosted/server posture is additive-first and does not rely on
dual-write.

Cutover sequence:

1. Capture one maintenance window: SQLite backup plus object-store snapshot or version
   set.
2. Export a deterministic SQLite runtime metadata snapshot with
   `python -m tools.ops.export_runtime_metadata_snapshot`.
3. Provision an empty Postgres target and apply Alembic head with
   `python -m tools.ops.upgrade_runtime_postgres_schema`.
4. Import the runtime metadata snapshot with
   `python -m tools.ops.import_runtime_metadata_snapshot`.
5. Run live parity against the Postgres target with
   `python -m tools.ops.check_runtime_metadata_parity`.
6. Only after parity succeeds, switch the hosted/server deployment to
   `GOAT_RUNTIME_METADATA_BACKEND=postgres`.

Rollback posture:

- do not mutate or drop SQLite tables as part of the initial hosted Postgres rollout
- keep the SQLite backup, runtime metadata snapshot, and object-store snapshot or
  version set from the same capture window
- if hosted Postgres cutover fails, restore the matched SQLite plus object-store set
  and rebuild or re-import the Postgres target from that same capture window
- treat workbench tasks/events, sandbox executions/logs, idempotency rows, and
  `conversations` as rollback-critical because they encode ordering and audit history,
  not just user content

## Validation and proof

Required proof for the shipped Phase 16D posture:

- repository contract tests for SQLite and Postgres implementations
- Alembic upgrade-to-head proof, including idempotent rerun on an already-upgraded
  target
- SQLite snapshot export plus Postgres import/parity proof across the full governed
  table family
- failure-path coverage for backend selection, empty-target import requirements,
  parity mismatches, recovery ordering, and append-only `conversations` behavior
- synced runbooks and governance artifacts:
  - `docs/operations/OPERATIONS.md`
  - `docs/operations/BACKUP_RESTORE.md`
  - `docs/operations/ROLLBACK.md`
  - `docs/architecture/STORAGE_EVOLUTION_DECISION_PACKAGE.md`
  - `docs/governance/PROJECT_STATUS.md`
  - `docs/governance/ROADMAP.md`
  - `docs/governance/ROADMAP_ARCHIVE.md`

## Residual boundaries

- hosted/server Postgres is opt-in; it is not the default local or desktop runtime
- future local/desktop storage-engine changes remain a separate follow-on if keeping
  SQLite there becomes a real cost
- this slice does not change frontend-visible contracts or widen authz capability
  promises

## Related artifacts

- [STORAGE_EVOLUTION_DECISION_PACKAGE.md](STORAGE_EVOLUTION_DECISION_PACKAGE.md)
- [OBJECT_STORAGE_CONTRACT.md](OBJECT_STORAGE_CONTRACT.md)
- [OPERATIONS.md](../operations/OPERATIONS.md)
- [BACKUP_RESTORE.md](../operations/BACKUP_RESTORE.md)
- [ROLLBACK.md](../operations/ROLLBACK.md)
- [PROJECT_STATUS.md](../governance/PROJECT_STATUS.md)
- [ROADMAP_ARCHIVE.md](../governance/ROADMAP_ARCHIVE.md)
