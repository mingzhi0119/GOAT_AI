# Storage Evolution Decision Package

Last updated: 2026-04-13

## Purpose

This document records the shipped storage boundary through **Phase 16C** and the
remaining decision guardrails for **Phase 16D**. It is both the closeout record for
the landed object-store contract and the stop sign that keeps runtime-database
evolution from starting without a separate compatibility package.

## Phase 16B closeout

Phase 16B is complete with a conservative outcome:

- persisted resource records now expose an explicit resource-ownership abstraction at the repository boundary
- repository contracts are explicit across sessions, artifacts, knowledge, media, workbench, and code sandbox persistence
- `knowledge` and `media` now follow the same injectable repository pattern already used by other runtime persistence seams
- Phase 16B intentionally did **not** change schema, read/write semantics, deployment shape, or public API behavior
- any future datastore-shape change still requires a new migration, compatibility, and rollback decision package before implementation starts

## Phase 16C landed decision

Phase 16C is complete with a conservative storage-decoupling outcome:

- file/blob payloads now persist through a canonical object-store contract instead of direct route or service path conventions
- the canonical application boundary is a `storage_key`; local filesystem `storage_path` remains a best-effort detail for local backends only
- shipped payloads on this boundary include knowledge source files, normalized knowledge text/metadata, local vector-index payloads, media uploads, chat artifacts, and workspace-output export artifacts
- the default backend is `local` at `GOAT_OBJECT_STORE_ROOT` (defaulting to `GOAT_DATA_DIR`); an `s3` backend is also supported through the same contract
- additive `storage_key` columns preserve read compatibility while runtime metadata remains in SQLite
- public API semantics, authz scope checks, artifact download behavior, and recoverable failure posture remain unchanged from the caller perspective

## Fixed constraints

- Preserve the current **SQLite-first** operational model for runtime metadata unless a separate Phase 16D decision package approves a different write path.
- Preserve the current **single-writer** safety assumptions for the runtime database.
- Keep **tenant scoping** explicit for persisted resources; object storage must not bypass repository-level authorization.
- Treat `storage_key` as the canonical application boundary for persisted blobs; `storage_path` is an implementation detail and may be empty for remote backends.
- Keep `local` object storage usable for development and desktop installs without source edits.
- Require explicit operator-visible backup/restore and rollback posture for both local and remote object-store modes.

## Current shipped storage boundary

- `knowledge_documents`: original uploads plus normalized text/metadata and vector-index payloads are keyed in the object store; SQLite metadata rows track ownership and `storage_key`.
- `chat_artifacts`: generated downloadables are keyed in the object store and still downloaded through the same artifact API contract.
- `media_uploads`: image attachments are keyed in the object store and remain caller-scoped through the existing authz behavior.
- `workspace-output exports`: exported workbench artifacts reuse the same artifact/object-store contract.
- Runtime metadata such as sessions, task rows, events, sandbox executions/logs, and idempotency records remain in SQLite.

## Shipped compatibility posture

- Schema changes are additive-first: `storage_key` columns were added without removing legacy local-path reads.
- Local backends may still resolve direct filesystem paths for efficient file responses.
- Remote backends may return no filesystem path and are served through proxied byte reads instead.
- Operator rollback must pair SQLite metadata with the matching object-store snapshot or remote restore point.

## Remaining open decision topics (Phase 16D)

### 1. Runtime persistence surfaces

- Identify the current SQLite-owned persistence surfaces that must move together, including sessions, artifacts metadata, knowledge metadata, workbench tasks/events/outputs, sandbox executions/logs, and idempotency rows.
- Preserve durable-task recovery, event ordering, and export/download behavior while changing the database engine.

### 2. Compatibility and migration ordering

- All new storage shapes must specify:
  - read compatibility with current SQLite rows
  - write compatibility during rollout
  - exact downgrade behavior after partial deployment
- If a future design requires new tables or indexes, define whether rollout is:
  - additive schema first, logic second
  - dual-read only
  - or temporary dual-write

### 3. Rollback and downgrade posture

- Every proposed migration must state:
  - whether rollback is metadata-only or data-transforming
  - whether old binaries can still read newly written rows
  - what operator action is required if rollback occurs after partial writes to the runtime database and the object store
- Avoid any design that requires irreversible backfill before read compatibility is proven.

### 4. Desktop/local carve-out and hosted posture

- Decide whether desktop and local development remain on SQLite while hosted/server deployments move to Postgres.
- Keep the current object-store contract stable so file/blob handling does not fork by deployment shape.

## Required sequence before Phase 16D

1. Approve the target runtime-database shape and hosted/local ownership story.
2. Document compatibility and rollback in `docs/operations/OPERATIONS.md`.
3. Introduce additive schema changes only.
4. Land dual-read logic if required.
5. Land write-path changes only after black-box and migration tests prove rollback safety.

## Out of scope for this document

- End-user identity
- New frontend capability exposure
- `/api/knowledge/answers` semantic changes
- Replacing SQLite during Phase 16C without a separate approved Phase 16D artifact
