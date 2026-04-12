# GOAT AI SQLite Backup and Restore

This runbook covers safe backup and restore for the chat/session SQLite database.

## Scope

- Source DB: `GOAT_LOG_PATH` (default `<repo>/var/chat_logs.db`); includes `sessions`, `session_messages`, and related tables (see [SESSION_MESSAGES_MIGRATION.md](../architecture/SESSION_MESSAGES_MIGRATION.md)).
- Backup files: timestamped `chat_logs_YYYYMMDD_HHMMSS.db`
- Default backup directory: `<repo>/backups` (override with `GOAT_BACKUP_DIR`)

## 1) Create a backup

```bash
python -m tools.ops.backup_chat_db
```

Optional overrides:

```bash
python -m tools.ops.backup_chat_db --src /path/to/chat_logs.db --dest-dir /path/to/backups --max-files 14
```

## 2) Verify backup integrity

Pick the newest backup and run integrity check:

```bash
sqlite3 /path/to/backups/chat_logs_YYYYMMDD_HHMMSS.db "PRAGMA integrity_check;"
```

Expected output:

```text
ok
```

Or run the scripted drill, which now exercises backup creation, restore-to-target, and rollback-to-original-copy in one pass:

```bash
python -m tools.ops.exercise_recovery_drill --src /path/to/chat_logs.db --backup-dir /path/to/backups --required-table sessions --required-table session_messages
```

## 3) Restore drill (staging or maintenance window)

1. Stop the API process.
2. Keep the current DB as a rollback copy.
3. Replace DB with backup.
4. Start API.
5. Validate health/readiness/history endpoints.

Example:

```bash
cp chat_logs.db chat_logs.pre_restore.db
cp /path/to/backups/chat_logs_YYYYMMDD_HHMMSS.db chat_logs.db
python -m tools.ops.post_deploy_check --base-url http://127.0.0.1:62606
```

## 4) Rollback from restore attempt

If restore validation fails:

```bash
cp chat_logs.pre_restore.db chat_logs.db
python -m tools.ops.post_deploy_check --base-url http://127.0.0.1:62606
```

## Notes

- SQLite backup is online-safe via `sqlite3.Connection.backup()` in `tools/ops/backup_chat_db.py`.
- `python -m tools.ops.exercise_recovery_drill` is the preferred non-production rehearsal path because it verifies backup integrity, restore bytes, and rollback bytes together instead of relying on a handwritten copy sequence.
- Keep backups on the same filesystem only for short-term recovery; copy to durable storage for disaster recovery.
