# Session messages table (Phase 15.4)

Normalized chat turns live in SQLite table **`session_messages`** (migration `008_session_messages.sql`). The legacy blob column **`sessions.messages`** remains the **canonical JSON snapshot** for chart metadata, knowledge attachments, and codec versioning until an explicit cutover.

## Dual-write

On every `log_service.upsert_session`, the service:

1. Writes the versioned JSON payload to `sessions.messages` (unchanged).
2. Replaces rows in `session_messages` for that `session_id` (delete + insert) so visible `user` / `assistant` / `system` messages match the payload’s `messages` array.

If the `session_messages` table is absent (pre-migration DB opened without running migrations), only the JSON path runs.

## Dual-read

`log_service.get_session` loads the JSON blob, then **if** `session_messages` has one or more rows for that session, the **visible message list** is taken from those rows (ordered by `seq`) while **envelope fields** (`chart_spec`, `file_context_prompt`, `knowledge_documents`, `version`, etc.) stay from the JSON dict when the blob is a versioned object.

If there are no normalized rows, behavior matches pre-15.4 (decode from JSON or legacy list only).

## Cutover (future)

A later phase may stop duplicating message text in JSON or make `session_messages` the sole source for chat rows. That requires a Decision Log entry, codec updates, and backward compatibility tests.

## Rollback

- **Schema:** restore from backup per [BACKUP_RESTORE.md](BACKUP_RESTORE.md); do not drop `sessions` without a plan.
- **App rollback:** older binaries that do not touch `session_messages` still read `sessions.messages`; rows in `session_messages` are ignored by those builds if they never query the table.

## Related

- [SESSION_SCHEMA.md](SESSION_SCHEMA.md) — versioned JSON shape.
- [BACKUP_RESTORE.md](BACKUP_RESTORE.md) — SQLite backup discipline.
