from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from backend.services.db_migrations import apply_migrations
from backend.services.runtime_metadata_inventory import RUNTIME_METADATA_TABLES
from backend.services.runtime_metadata_snapshot import (
    SNAPSHOT_FORMAT_VERSION,
    export_sqlite_runtime_metadata_snapshot,
    write_sqlite_runtime_metadata_snapshot,
)


class RuntimeMetadataSnapshotTests(unittest.TestCase):
    def test_export_snapshot_includes_all_governed_tables(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db_path = Path(tmp) / "runtime.db"
            apply_migrations(db_path)

            snapshot = export_sqlite_runtime_metadata_snapshot(db_path)

            self.assertEqual(
                SNAPSHOT_FORMAT_VERSION,
                snapshot["snapshot_format_version"],
            )
            self.assertEqual("sqlite", snapshot["source_backend"])
            self.assertEqual(
                set(RUNTIME_METADATA_TABLES),
                set(snapshot["tables"].keys()),
            )
            for table_name in RUNTIME_METADATA_TABLES:
                if table_name == "schema_migrations":
                    self.assertTrue(snapshot["tables"][table_name])
                else:
                    self.assertEqual([], snapshot["tables"][table_name])

    def test_export_snapshot_orders_rows_deterministically(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db_path = Path(tmp) / "runtime.db"
            out_path = Path(tmp) / "snapshot.json"
            apply_migrations(db_path)

            import sqlite3

            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO sessions
                        (id, title, model, schema_version, created_at, updated_at, messages, owner_id, tenant_id, principal_id)
                    VALUES
                        ('s-2', 'Second', 'llama3', 1, '2026-04-13T10:00:02Z', '2026-04-13T10:00:02Z', '[]', '', 'tenant:default', ''),
                        ('s-1', 'First', 'llama3', 1, '2026-04-13T10:00:01Z', '2026-04-13T10:00:01Z', '[]', '', 'tenant:default', '')
                    """
                )
                conn.execute(
                    """
                    INSERT INTO session_messages
                        (session_id, seq, role, content, image_attachment_ids, artifacts_json, created_at)
                    VALUES
                        ('s-1', 1, 'assistant', 'world', NULL, NULL, '2026-04-13T10:00:04Z'),
                        ('s-1', 0, 'user', 'hello', NULL, NULL, '2026-04-13T10:00:03Z')
                    """
                )
                conn.execute(
                    """
                    INSERT INTO workbench_tasks
                        (id, task_kind, status, prompt, session_id, project_id, knowledge_document_ids, connector_ids, source_ids, error_detail, result_text, result_citations_json, created_at, updated_at, auth_scopes_json, credential_id, auth_mode, owner_id, tenant_id, principal_id)
                    VALUES
                        ('task-b', 'plan', 'queued', 'second', NULL, NULL, '[]', '[]', '[]', NULL, NULL, NULL, '2026-04-13T10:01:02Z', '2026-04-13T10:01:02Z', '[]', '', '', '', 'tenant:default', ''),
                        ('task-a', 'plan', 'queued', 'first', NULL, NULL, '[]', '[]', '[]', NULL, NULL, NULL, '2026-04-13T10:01:01Z', '2026-04-13T10:01:01Z', '[]', '', '', '', 'tenant:default', '')
                    """
                )
                conn.execute(
                    """
                    INSERT INTO workbench_task_events
                        (task_id, seq, event_type, created_at, status, message, metadata_json)
                    VALUES
                        ('task-a', 2, 'task.completed', '2026-04-13T10:01:03Z', 'completed', 'done', '{}'),
                        ('task-a', 1, 'task.queued', '2026-04-13T10:01:01Z', 'queued', 'queued', '{}')
                    """
                )
                conn.commit()

            written = write_sqlite_runtime_metadata_snapshot(
                db_path=db_path,
                out_path=out_path,
            )

            self.assertEqual(out_path, written)
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(
                ["s-1", "s-2"],
                [row["id"] for row in payload["tables"]["sessions"]],
            )
            self.assertEqual(
                [0, 1],
                [row["seq"] for row in payload["tables"]["session_messages"]],
            )
            self.assertEqual(
                ["task-a", "task-b"],
                [row["id"] for row in payload["tables"]["workbench_tasks"]],
            )
            self.assertEqual(
                [1, 2],
                [row["seq"] for row in payload["tables"]["workbench_task_events"]],
            )

    def test_export_snapshot_fails_when_inventory_is_incomplete(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db_path = Path(tmp) / "runtime.db"

            import sqlite3

            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    "CREATE TABLE schema_migrations (id TEXT PRIMARY KEY, applied_at TEXT, checksum TEXT)"
                )
                conn.commit()

            with self.assertRaisesRegex(RuntimeError, "missing tables"):
                export_sqlite_runtime_metadata_snapshot(db_path)


if __name__ == "__main__":
    unittest.main()
