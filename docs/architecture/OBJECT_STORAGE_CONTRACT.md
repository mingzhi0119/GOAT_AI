# Object Storage Contract

Last updated: 2026-04-13

## Purpose

This document defines the canonical Phase 16C storage boundary for persisted file
and blob payloads. It captures the application-visible contract only; it does not
approve or describe Phase 16D runtime-database migration work.

## Scope

The object-store boundary owns persisted bytes for:

- knowledge source uploads
- normalized knowledge text and metadata payloads
- vector-index payloads
- media uploads
- chat artifacts
- workspace-output export artifacts

SQLite remains the source of truth for runtime metadata, ownership, and download
authorization. The object store owns blob bytes, not caller visibility rules.

## Stable application contract

- Application and API layers treat blob references as opaque `storage_key` values.
- HTTP payloads continue to expose opaque ids such as `document_id`,
  `attachment_id`, `artifact_id`, and server-provided `download_url`.
- `download_url` remains the stable `/api/artifacts/{artifact_id}` contract, not a
  backend-specific filesystem path or storage-provider URL.
- `storage_path` is a compatibility/local-optimization field only. New behavior
  must not require callers, routers, or frontend code to infer semantics from a
  filesystem path.

## Key layout

Current logical key families are:

- `artifacts/<artifact_id>/<filename>`
- `media/<attachment_id>/image.bin`
- `uploads/media/<attachment_id>/meta.txt`
- `knowledge/<document_id>/original/source.<ext>`
- `knowledge/<document_id>/normalized/extracted.txt`
- `knowledge/<document_id>/normalized/metadata.json`
- `vector-index/<backend_name>/<document_id>.json`

These shapes are an internal backend contract. They may be used by operators for
backup/restore tooling, but they are not part of the public HTTP API.

## Backend modes

### Local

- `GOAT_OBJECT_STORE_BACKEND=local`
- bytes are stored under `GOAT_OBJECT_STORE_ROOT`
- `GOAT_OBJECT_STORE_ROOT` defaults to `GOAT_DATA_DIR`
- local file responses may use a filesystem path optimization when one exists

### S3-compatible

- `GOAT_OBJECT_STORE_BACKEND=s3`
- required bucket: `GOAT_OBJECT_STORE_BUCKET`
- optional prefix: `GOAT_OBJECT_STORE_PREFIX`
- optional endpoint/region/credentials configure the selected S3-compatible provider

The backend contract is the same in both modes: callers still see opaque ids and
API-routed downloads.

## Failure and compatibility posture

- Writes are additive-first: blob bytes are written before the corresponding
  metadata row is committed.
- Repository-write failure must delete the just-written object when possible.
- Reads prefer `storage_key`; legacy/local file-path fallback remains for
  recoverability and migration safety.
- Rollback and recovery must treat runtime metadata plus object bytes as one
  operator-visible unit, even while SQLite remains the metadata store.

## Non-goals

- no frontend-visible storage-engine field
- no direct object-store URL exposure in API payloads
- no Phase 16D runtime-database migration guidance in this document
