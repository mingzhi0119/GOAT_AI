# GOAT AI Runtime Backup and Restore

This runbook covers safe backup and restore for the SQLite runtime metadata store and
the paired object-store payloads that Phase 16C moved behind the shared storage
boundary.

## Scope

- Runtime metadata DB: `GOAT_LOG_PATH` (default `<repo>/var/chat_logs.db`); includes
  `sessions`, `session_messages`, artifacts metadata, knowledge/media metadata, and
  related tables whose blob references now flow through `storage_key`.
- Object payloads:
  - `GOAT_OBJECT_STORE_BACKEND=local`: files live under `GOAT_OBJECT_STORE_ROOT`
    (defaulting to `GOAT_DATA_DIR`)
  - `GOAT_OBJECT_STORE_BACKEND=s3`: files live in
    `GOAT_OBJECT_STORE_BUCKET` plus optional `GOAT_OBJECT_STORE_PREFIX`
- The checked-in tooling (`python -m tools.ops.backup_chat_db` and
  `python -m tools.ops.exercise_recovery_drill`) currently proves the SQLite side
  only. Object-payload capture is still operator-owned.

## 1) Create a paired backup window

1. Quiesce writes or stop the API process for the maintenance window.
2. Back up SQLite metadata:

```bash
python -m tools.ops.backup_chat_db
```

Optional overrides:

```bash
python -m tools.ops.backup_chat_db --src /path/to/chat_logs.db --dest-dir /path/to/backups --max-files 14
```

3. Capture object payloads from the same window:
   - local backend: copy or snapshot `GOAT_OBJECT_STORE_ROOT`
   - `s3` backend: capture a provider-native snapshot/version set for the configured
     bucket/prefix
4. Export a deterministic runtime metadata snapshot for the same SQLite window:

```bash
python -m tools.ops.export_runtime_metadata_snapshot --out /path/to/backups/runtime_metadata_YYYYMMDD_HHMMSS.json
```

5. Record the SQLite backup filename, the runtime metadata snapshot filename, and the object-store snapshot identifier
   together. They are one restore set.

## 2) Verify backup integrity

SQLite integrity:

```bash
sqlite3 /path/to/backups/chat_logs_YYYYMMDD_HHMMSS.db "PRAGMA integrity_check;"
```

Expected output:

```text
ok
```

SQLite recovery drill:

```bash
python -m tools.ops.exercise_recovery_drill --src /path/to/chat_logs.db --backup-dir /path/to/backups --required-table sessions --required-table session_messages
```

Runtime metadata snapshot verification:

- `python -m tools.ops.export_runtime_metadata_snapshot` should succeed against the
  chosen backup candidate before you treat it as migration-ready
- the exported JSON should include the full governed table family, including
  sessions, artifacts, knowledge/media metadata, workbench tasks/events/outputs,
  sandbox executions/events/logs, idempotency rows, and `schema_migrations`

Object-payload verification:

- local backend: confirm the copied `GOAT_OBJECT_STORE_ROOT` contains the expected
  prefixes (`knowledge/`, `media/`, `artifacts/`) when those features are in use
- `s3` backend: confirm the retained bucket/prefix snapshot or version set covers the
  expected keyspace before treating the backup set as complete

## 3) Restore drill (staging or maintenance window)

1. Stop the API process.
2. Keep the current SQLite DB and current object snapshot as rollback copies.
3. Restore the SQLite DB from the chosen backup.
4. Restore the matching object-store snapshot from the same capture window.
5. Start the API.
6. Validate `GET /api/health`, `GET /api/ready`, history reads, and at least one
   object-backed path that matters for the incident (`/api/artifacts/{artifact_id}`,
   knowledge ingestion/search, or media upload/read).

Local-backend example:

```bash
cp chat_logs.db chat_logs.pre_restore.db
cp /path/to/backups/chat_logs_YYYYMMDD_HHMMSS.db chat_logs.db
cp -R /path/to/object-store-snapshots/snapshot-YYYYMMDD_HHMMSS ./var/data
python -m tools.ops.post_deploy_check --base-url http://127.0.0.1:62606
```

## 4) Rollback from a failed restore attempt

If restore validation fails, revert both halves of the restore set:

```bash
cp chat_logs.pre_restore.db chat_logs.db
python -m tools.ops.post_deploy_check --base-url http://127.0.0.1:62606
```

Then restore the previous object-store snapshot that matched `chat_logs.pre_restore.db`
before re-opening writes.

## Notes

- SQLite backup is online-safe via `sqlite3.Connection.backup()` in
  `tools/ops/backup_chat_db.py`.
- `python -m tools.ops.export_runtime_metadata_snapshot` is the deterministic runtime metadata snapshot path for current Phase 16D parity work; keep it paired with the raw SQLite backup rather than treating it as a replacement.
- `python -m tools.ops.exercise_recovery_drill` remains the preferred non-production
  rehearsal path for SQLite because it verifies backup integrity, restore bytes, and
  rollback bytes together instead of relying on a handwritten copy sequence.
- The SQLite drill does not yet restore object-store payloads for you; treat
  `GOAT_OBJECT_STORE_ROOT` or the configured bucket/prefix snapshot as a required
  companion artifact.
- For `GOAT_OBJECT_STORE_BACKEND=s3`, provider-native versioning or snapshot tooling
  should be rehearsed before the remote backend is enabled on a production-like host.
