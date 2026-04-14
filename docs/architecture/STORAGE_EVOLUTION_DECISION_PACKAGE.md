# Storage Evolution Decision Package

Last updated: 2026-04-13

## Purpose

This document records the shipped storage boundary through **Phase 16D**. It is the
high-level closeout record for the landed object-store contract plus the hosted/server
runtime-metadata Postgres posture that now sits behind the same repository and
authorization boundaries.

## Phase 16B closeout

Phase 16B completed with a conservative ownership-first outcome:

- persisted resource records expose explicit resource ownership at repository
  boundaries
- repository contracts are explicit across sessions, artifacts, knowledge, media,
  workbench, and code sandbox persistence
- `knowledge` and `media` now follow the same injectable repository pattern already
  used by the other runtime persistence seams
- Phase 16B did **not** change schema, deployment shape, or public API behavior

## Phase 16C landed decision

Phase 16C completed the file/blob storage decoupling work:

- file/blob payloads now persist through a canonical object-store contract instead of
  direct route or service path conventions
- the canonical application boundary is `storage_key`; local filesystem
  `storage_path` remains a best-effort detail for local backends only
- shipped payloads on this boundary include knowledge source files, normalized
  knowledge text/metadata, local vector-index payloads, media uploads, chat
  artifacts, and workspace-output export artifacts
- the default backend is `local` at `GOAT_OBJECT_STORE_ROOT` (defaulting to
  `GOAT_DATA_DIR`); an `s3` backend is also supported through the same contract
- additive `storage_key` columns preserved read compatibility while runtime metadata
  stayed on SQLite
- public API semantics, caller-scoped authz behavior, and artifact download behavior
  stayed stable from the user perspective

## Phase 16D landed decision

Phase 16D is now complete for the hosted/server opt-in posture:

- runtime metadata can now use `GOAT_RUNTIME_METADATA_BACKEND=postgres` together with
  `GOAT_RUNTIME_POSTGRES_DSN` when `GOAT_DEPLOY_MODE=2`
- local development and desktop installs remain on SQLite by default
- Alembic under `backend/alembic/` owns hosted/server Postgres schema truth
- the governed runtime-metadata family moves as one unit, including
  `conversations`, sessions, session messages, idempotency rows, chat artifacts,
  knowledge metadata, media metadata, workbench tasks/events/outputs, sandbox
  executions/events/logs, and `schema_migrations`
- hosted cutover uses deterministic SQLite snapshot export plus Postgres import and
  live parity validation instead of long-lived dual-write
- rollback posture remains additive-first: restore the matched SQLite snapshot and
  object-store snapshot or version set from the same capture window, then rebuild or
  re-import the Postgres target if needed

## Shipped compatibility posture

- `storage_key` remains the canonical application boundary for persisted blobs;
  `storage_path` is an implementation detail and may be empty for remote backends
- local object storage may still resolve direct filesystem paths for efficient file
  responses
- remote object storage may return no filesystem path and is served through proxied
  byte reads instead
- hosted/server Postgres keeps the existing repository and service contracts intact,
  so HTTP/API, authz, artifact/object-store, event ordering, and recovery semantics
  do not fork by storage engine
- local and desktop remain SQLite-first, while hosted/server Postgres is opt-in and
  proven through import/parity plus rollback runbooks

## Current shipped storage boundary

- `knowledge_documents`: original uploads plus normalized text/metadata and
  vector-index payloads are keyed in the object store; metadata rows track ownership
  and `storage_key`
- `chat_artifacts`: generated downloadables are keyed in the object store and still
  downloaded through the stable artifact API contract
- `media_uploads`: image attachments are keyed in the object store and remain
  caller-scoped through the existing authz behavior
- `workspace-output exports`: exported workbench artifacts reuse the same
  artifact/object-store contract
- runtime metadata now defaults to SQLite for local/desktop and may opt into
  Postgres for hosted/server deployments without changing the user-facing contract

## Out of scope for this document

- end-user identity
- new frontend capability exposure
- `/api/knowledge/answers` semantic changes
- future local/desktop storage-engine changes beyond the shipped SQLite default

## Related artifacts

- [POSTGRES_RUNTIME_PERSISTENCE_DECISION_PACKAGE.md](POSTGRES_RUNTIME_PERSISTENCE_DECISION_PACKAGE.md)
- [OBJECT_STORAGE_CONTRACT.md](OBJECT_STORAGE_CONTRACT.md)
- [OPERATIONS.md](../operations/OPERATIONS.md)
- [BACKUP_RESTORE.md](../operations/BACKUP_RESTORE.md)
- [ROLLBACK.md](../operations/ROLLBACK.md)
- [ROADMAP_ARCHIVE.md](../governance/ROADMAP_ARCHIVE.md)
