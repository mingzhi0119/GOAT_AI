# Storage Evolution Decision Package

Last updated: 2026-04-10

## Purpose

This document captures the design boundary for **Phase 16B**. It is intentionally a
decision package, not an implementation approval. No datastore migration, dual-write,
or contract change should start until the questions below are explicitly resolved.

## Fixed constraints

- Preserve the current **SQLite-first** operational model unless a separate decision log approves a different write path.
- Preserve the current **single-writer** safety assumptions for the deployed app.
- Keep **tenant scoping** explicit for persisted resources; Phase 16A and 16C remain the source of truth for authorization semantics.
- Do not weaken existing rollback expectations for `sessions`, `chat_artifacts`, `knowledge_documents`, `knowledge ingestions`, or `media_uploads`.

## Current resource boundary inventory

- `sessions`: tenant-scoped today; still carries legacy owner compatibility.
- `chat_artifacts`: tenant-scoped and associated with a parent session.
- `knowledge_documents`: tenant-scoped; read/write decisions already flow through resource authorization.
- `media_uploads`: tenant-scoped; vision access follows the same authorization envelope.
- Supporting records such as session messages and ingestion/chunk metadata inherit resource boundaries indirectly and should not drift from their parent resource.

## Decision topics

### 1. Resource ownership model

- Decide whether `tenant_id` + `principal_id` on each row remains the long-term model, or whether the system should move toward a more explicit resource-ownership abstraction at the repository boundary.
- If ownership becomes more explicit, the change must remain additive first and preserve reads for current persisted rows.

### 2. Compatibility strategy

- All new storage shapes must specify:
  - read compatibility with current SQLite rows
  - write compatibility during rollout
  - exact downgrade behavior after partial deployment
- If a future design requires new tables or indexes, define whether rollout is:
  - additive schema first, logic second
  - dual-read only
  - or temporary dual-write

### 3. Rollback strategy

- Every proposed migration must state:
  - whether rollback is metadata-only or data-transforming
  - whether old binaries can still read newly written rows
  - what operator action is required if rollback occurs after partial writes
- Avoid any design that requires irreversible backfill before read compatibility is proven.

### 4. Multi-instance and external storage posture

- Decide whether future externalization is:
  - an adapter swap that preserves the current repository contract, or
  - a broader consistency-model change
- Until that decision is explicit, Phase 16B must assume the current single-instance write contract remains authoritative.

## Recommended implementation sequence after approval

1. Approve the target storage shape and ownership story.
2. Document compatibility and rollback in `docs/OPERATIONS.md`.
3. Introduce additive schema changes only.
4. Land dual-read logic if required.
5. Land write-path changes only after black-box and migration tests prove rollback safety.

## Out of scope for this document

- End-user identity
- New frontend capability exposure
- `/api/knowledge/answers` semantic changes
- Replacing SQLite during Phase 16B without a separate approved decision log
