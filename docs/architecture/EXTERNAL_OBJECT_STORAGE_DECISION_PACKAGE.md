# External Object Storage Decision Package

Last updated: 2026-04-13

## Purpose

Govern the Phase 16C change that moves persisted file/blob payloads behind a shared
object-store boundary without widening the public HTTP contract or replacing the
SQLite-owned runtime metadata store.

## Context

Before Phase 16C, uploads, media, generated artifacts, and knowledge/vector payloads
were tied directly to local filesystem paths under `GOAT_DATA_DIR`. That was simple
for a single-host deployment, but it made stateless or multi-node rollout shapes
depend on one application node's disk layout and leaked path assumptions into service
boundaries.

A lightweight decision record is insufficient here because the change affects:

- compatibility for already persisted rows
- rollout ordering across settings, migrations, service code, and runbooks
- rollback posture when remote object storage is enabled
- operator-visible backup/restore responsibilities

## Fixed constraints

- Preserve the current public API, authorization semantics, and artifact download
  behavior.
- Keep local development and desktop usable without requiring cloud infrastructure.
- Land additively first so existing rows and local-path deployments stay readable
  during rollout.
- Do not couple this slice to Phase 16D Postgres runtime persistence.

## Decision

Adopt one canonical object-store boundary in `goat_ai.uploads` and route persisted
blob payloads through it.

The shipped shape is:

- `GOAT_OBJECT_STORE_BACKEND=local` by default, rooted at `GOAT_OBJECT_STORE_ROOT`
  and defaulting to `GOAT_DATA_DIR`
- optional `GOAT_OBJECT_STORE_BACKEND=s3` using the configured
  bucket/prefix/endpoint credentials
- stable `storage_key` persistence for `knowledge_documents`, `chat_artifacts`, and
  `media_uploads`
- continued `storage_path` population for local backends so local file responses and
  legacy reads remain compatible
- knowledge originals, normalized text/metadata, vector-index payloads, media
  attachments, generated chat artifacts, and workspace-output export artifacts all use
  the same object-store contract

## Options considered

- Keep direct `GOAT_DATA_DIR` path writes:
  - rejected because it keeps application-node disk layout as the contract
- Move immediately to remote-only object storage:
  - rejected because it breaks local development and desktop expectations for no
    practical gain
- Chosen hybrid boundary:
  - one contract, local default, remote-capable backend swap, additive metadata
    rollout

## Compatibility strategy

- Add `storage_key` columns with safe defaults before switching write paths.
- Preserve reads for older rows through existing `storage_path` fallback behavior.
- Local backends continue to expose a filesystem path, so old binaries can still read
  newly written local rows through `storage_path` if rollback happens before remote
  storage is enabled.
- Remote backends keep the HTTP/API contract unchanged, but older binaries that do not
  understand `storage_key` cannot serve newly written remote objects. Remote rollback
  therefore requires keeping a Phase 16C-capable binary in place or restoring a
  matched pre-cutover SQLite + object snapshot.

## Migration or rollout sequence

1. Add object-store configuration and one shared storage implementation surface.
2. Add additive `storage_key` columns for knowledge, artifacts, and media rows.
3. Switch knowledge upload/ingestion, media, artifact persistence, and export paths to
   write via the object store.
4. Keep dual-read compatibility through `storage_key` first and `storage_path`
   fallback.
5. Update operator runbooks, API reference wording, and storage-governance tests.

## Rollback strategy

- Schema rollback is additive-first; do not drop `storage_key` columns during a normal
  rollback.
- Local object-store deployments can usually roll back code without losing access to
  newly written blobs because `storage_path` still points to a readable file.
- Remote object-store deployments are not safely readable by pre-Phase-16C binaries.
  If rollback crosses the object-store cutover, operators must restore the matching
  SQLite backup and object-store snapshot from the same capture window.
- Treat backup/restore and rollback as paired SQLite + object-store operations for any
  incident that affected uploads, media, knowledge payloads, or generated artifacts.

## Validation and proof

- Tests:
  - `__tests__/backend/services/test_object_storage.py`
  - `__tests__/backend/services/test_artifact_service.py`
  - `__tests__/backend/services/test_media_service.py`
  - `__tests__/backend/services/test_knowledge_pipeline.py`
  - `__tests__/backend/services/test_knowledge_service.py`
  - `__tests__/backend/services/test_db_migrations.py`
  - `__tests__/contracts/test_api_blackbox_contract.py`
  - `__tests__/contracts/test_api_authz.py`
- Contracts or generated artifacts:
  - `backend/migrations/022_storage_object_keys.sql`
  - `docs/api/API_REFERENCE.md`
- Workflow or runbook links:
  - `docs/operations/OPERATIONS.md`
  - `docs/operations/BACKUP_RESTORE.md`
  - `docs/operations/ROLLBACK.md`

## Open questions

- What provider-level versioning or retention policy should be required before
  `GOAT_OBJECT_STORE_BACKEND=s3` is treated as production-ready?
- When Phase 16D replaces SQLite runtime metadata in hosted/server deployments, which
  rollout constraints should be shared with this object-store layer and which should
  stay independent?

## Related artifacts

- Roadmap item: `docs/governance/ROADMAP.md` Phase 16 storage evolution
- Status or operations docs:
  - `docs/governance/PROJECT_STATUS.md`
  - `docs/governance/ROADMAP_ARCHIVE.md`
  - `docs/operations/OPERATIONS.md`
  - `docs/operations/BACKUP_RESTORE.md`
  - `docs/operations/ROLLBACK.md`
- Related PRs or follow-ups:
  - additive `storage_key` rollout in `backend/migrations/022_storage_object_keys.sql`
  - Phase 16D Postgres-backed runtime persistence remains a separate follow-on
