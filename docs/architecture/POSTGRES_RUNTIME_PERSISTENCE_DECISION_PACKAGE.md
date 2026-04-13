# Postgres Runtime Persistence Decision Package

Last updated: 2026-04-13

## Purpose

Define the Phase 16D boundary for moving hosted/server runtime metadata off the
current `SQLite-first` single-writer shape without weakening API, authorization,
recovery, or rollback semantics.

## Context

Phase 16C is now complete: uploads, media, generated artifacts, normalized knowledge
payloads, vector-index payloads, and workspace-export blobs sit behind the shared
object-store contract. The remaining storage-evolution work is the runtime metadata
plane.

That metadata still lives in SQLite today and covers more than chat history. The
current persistence surface includes:

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

A lightweight decision record is not enough here because Phase 16D changes deployment
shape, migration ordering, rollback posture, and operator-visible recovery behavior.

## Fixed constraints

- Preserve the current HTTP/API contract, caller-scoped authz behavior, and recovery
  semantics.
- Keep object/blob payloads on the Phase 16C object-store boundary; Phase 16D changes
  runtime metadata only.
- Keep local development and desktop on SQLite until hosted/server Postgres behavior
  is mechanically proven.
- Land additively first; avoid irreversible backfill or in-place SQLite mutation
  before compatibility proof exists.

## Decision

Phase 16D should target a hosted/server-only Postgres runtime metadata backend first,
while SQLite remains the authoritative local/desktop backend.

Implementation must follow these rules:

- preserve one repository/service contract so storage-engine choice stays behind the
  current backend boundaries
- move the runtime metadata surfaces as one governed family rather than through
  unrelated table-by-table cutovers that would break event ordering or recovery
  assumptions
- keep `storage_key` as the durable link from metadata rows to the Phase 16C
  object-store payloads
- prefer explicit export/import plus parity validation over long-lived dual-write for
  hosted cutover, because idempotency, queued-task ordering, and replayable log/event
  guarantees are harder to prove under mixed primaries

## Options considered

- Keep SQLite for every deployment:
  - rejected because it preserves the current single-writer hosting ceiling
- Replace SQLite everywhere in one cutover:
  - rejected because it needlessly breaks desktop/local expectations and creates a
    large rollback blast radius
- Hosted/server Postgres first, SQLite retained for local/desktop:
  - chosen because it isolates hosted needs without forcing an immediate local-runtime
    rewrite

## Compatibility strategy

- SQLite remains the default backend until a separate hosted rollout is explicitly
  enabled.
- Postgres schema rollout must be additive and mirror the current repository-facing
  invariants before any hosted write-path cutover.
- Hosted cutover should use a deterministic SQLite snapshot export/import path plus
  parity validation rather than assuming cross-engine live dual-write.
- Downgrade/rollback after hosted cutover requires restoring the last known-good
  SQLite snapshot and the matching Phase 16C object-store snapshot from the same
  capture window.
- Desktop/local binaries must not depend on Postgres-only behavior while SQLite
  remains the shipped local backend.

## Migration or rollout sequence

1. Approve this package as the only valid Phase 16D implementation posture.
2. Add backend-selection/config truth for runtime metadata, keeping SQLite default and
   desktop/local behavior unchanged.
3. Introduce Postgres schema/migration assets that preserve the current repository
   invariants and tenancy fields.
4. Build deterministic SQLite export/import tooling and parity checks for the full
   runtime metadata surface.
5. Add repository-adapter tests that prove SQLite and Postgres implementations obey
   the same contracts.
6. Enable hosted/server Postgres writes only after compatibility, rollback, and
   failure-path coverage are green.
7. Revisit desktop/local storage-engine expectations only in a later, separate slice
   if keeping SQLite there becomes a real cost.

## Rollback strategy

- Do not mutate or drop SQLite tables as part of the initial hosted Postgres rollout.
- If hosted Postgres cutover fails, return to the last known-good SQLite snapshot and
  restore the matching object-store snapshot/version set from the same capture window.
- Avoid any design that requires old binaries to read partially migrated Postgres
  state.
- Treat workbench tasks/events, sandbox executions/logs, and idempotency rows as
  rollback-critical data because they encode recovery ordering rather than just user
  content.

## Validation and proof

- Tests:
  - repository contract tests for SQLite and Postgres implementations
  - migration/export/import parity tests across the full runtime metadata surface
  - black-box authz and artifact/knowledge/media/workbench regression tests against
    the selected backend
  - failure-path coverage for rollback and recovery ordering
- Contracts or generated artifacts:
  - `docs/api/API_REFERENCE.md`
  - `docs/architecture/STORAGE_EVOLUTION_DECISION_PACKAGE.md`
  - `docs/architecture/EXTERNAL_OBJECT_STORAGE_DECISION_PACKAGE.md`
- Workflow or runbook links:
  - `docs/operations/OPERATIONS.md`
  - `docs/operations/BACKUP_RESTORE.md`
  - `docs/operations/ROLLBACK.md`
  - `python -m tools.ops.export_runtime_metadata_snapshot`

Current landed groundwork for this package:

- runtime backend selection and fail-fast seams now live in
  `goat_ai/config/settings.py` plus `backend/services/runtime_persistence.py`
- the governed runtime metadata family now has one canonical inventory in
  `backend/services/runtime_metadata_inventory.py`
- deterministic SQLite export proof now starts with
  `python -m tools.ops.export_runtime_metadata_snapshot`

## Open questions

- Which migration/tooling stack should own Postgres schema truth for this repo
  (`sqlite3`-style SQL files, Alembic, or another additive-only path)?
- Which runtime tables, if any, need Postgres-specific sequence/partition strategy for
  workbench events or sandbox logs at hosted scale?
- Does the legacy `conversations` table remain part of the hosted compatibility
  surface, or can it eventually become SQLite-only historical baggage after separate
  proof?

## Related artifacts

- Roadmap item: `docs/governance/ROADMAP.md` Phase 16D
- Status or operations docs:
  - `docs/governance/PROJECT_STATUS.md`
  - `docs/operations/OPERATIONS.md`
  - `docs/operations/BACKUP_RESTORE.md`
  - `docs/operations/ROLLBACK.md`
- Related PRs or follow-ups:
  - `docs/architecture/STORAGE_EVOLUTION_DECISION_PACKAGE.md`
  - `docs/architecture/EXTERNAL_OBJECT_STORAGE_DECISION_PACKAGE.md`
