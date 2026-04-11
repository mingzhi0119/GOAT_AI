"""Tests for ``backend/services/db_migrations`` (Phase 13 §13.0)."""

from __future__ import annotations

import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.services.db_migrations import apply_migrations

_REPO_MIGRATIONS = Path(__file__).resolve().parents[1] / "backend" / "migrations"


class DbMigrationsTests(unittest.TestCase):
    def test_fresh_database_applies_all_migrations(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db_path = Path(tmp) / "t.db"
            apply_migrations(db_path)
            conn = sqlite3.connect(db_path)
            try:
                rows = conn.execute(
                    "SELECT id FROM schema_migrations ORDER BY id"
                ).fetchall()
                ids = [r[0] for r in rows]
                self.assertEqual(
                    ids,
                    [
                        "001_schema_migrations",
                        "002_core_tables",
                        "003_add_conversations_user_name",
                        "004_add_conversations_session_id",
                        "005_add_idempotency_keys",
                        "006_add_sessions_schema_version",
                        "007_add_knowledge_tables",
                        "008_session_messages",
                        "009_sessions_owner_id",
                        "010_chat_artifacts",
                        "011_authorization_tenancy",
                        "012_knowledge_media_authorization",
                        "013_workbench_tasks",
                        "014_workbench_task_result_text",
                        "015_workbench_task_events",
                        "016_workbench_task_result_citations",
                        "017_workbench_task_source_and_auth_state",
                        "018_code_sandbox_executions",
                    ],
                )
                cols = [
                    r[1]
                    for r in conn.execute("PRAGMA table_info(conversations)").fetchall()
                ]
                self.assertIn("user_name", cols)
                self.assertIn("session_id", cols)
                session_cols = [
                    r[1] for r in conn.execute("PRAGMA table_info(sessions)").fetchall()
                ]
                self.assertIn("schema_version", session_cols)
                self.assertIn("owner_id", session_cols)
                self.assertIn("tenant_id", session_cols)
                self.assertIn("principal_id", session_cols)
                knowledge_cols = [
                    r[1]
                    for r in conn.execute(
                        "PRAGMA table_info(knowledge_documents)"
                    ).fetchall()
                ]
                self.assertIn("storage_path", knowledge_cols)
                self.assertIn("owner_id", knowledge_cols)
                self.assertIn("tenant_id", knowledge_cols)
                self.assertIn("principal_id", knowledge_cols)
                ingestion_cols = [
                    r[1]
                    for r in conn.execute(
                        "PRAGMA table_info(knowledge_ingestions)"
                    ).fetchall()
                ]
                self.assertIn("vector_backend", ingestion_cols)
                chunk_cols = [
                    r[1]
                    for r in conn.execute(
                        "PRAGMA table_info(knowledge_chunks)"
                    ).fetchall()
                ]
                self.assertIn("vector_ref", chunk_cols)
                session_message_cols = [
                    r[1]
                    for r in conn.execute(
                        "PRAGMA table_info(session_messages)"
                    ).fetchall()
                ]
                self.assertIn("artifacts_json", session_message_cols)
                artifact_cols = [
                    r[1]
                    for r in conn.execute(
                        "PRAGMA table_info(chat_artifacts)"
                    ).fetchall()
                ]
                self.assertIn("storage_path", artifact_cols)
                self.assertIn("tenant_id", artifact_cols)
                self.assertIn("principal_id", artifact_cols)
                media_cols = [
                    r[1]
                    for r in conn.execute("PRAGMA table_info(media_uploads)").fetchall()
                ]
                self.assertIn("tenant_id", media_cols)
                self.assertIn("principal_id", media_cols)
                workbench_cols = [
                    r[1]
                    for r in conn.execute(
                        "PRAGMA table_info(workbench_tasks)"
                    ).fetchall()
                ]
                self.assertIn("status", workbench_cols)
                self.assertIn("prompt", workbench_cols)
                self.assertIn("knowledge_document_ids", workbench_cols)
                self.assertIn("connector_ids", workbench_cols)
                self.assertIn("source_ids", workbench_cols)
                self.assertIn("owner_id", workbench_cols)
                self.assertIn("tenant_id", workbench_cols)
                self.assertIn("principal_id", workbench_cols)
                self.assertIn("result_text", workbench_cols)
                self.assertIn("result_citations_json", workbench_cols)
                self.assertIn("auth_scopes_json", workbench_cols)
                self.assertIn("credential_id", workbench_cols)
                self.assertIn("auth_mode", workbench_cols)
                workbench_event_cols = [
                    r[1]
                    for r in conn.execute(
                        "PRAGMA table_info(workbench_task_events)"
                    ).fetchall()
                ]
                self.assertIn("task_id", workbench_event_cols)
                self.assertIn("seq", workbench_event_cols)
                self.assertIn("event_type", workbench_event_cols)
                self.assertIn("metadata_json", workbench_event_cols)
                sandbox_cols = [
                    r[1]
                    for r in conn.execute(
                        "PRAGMA table_info(code_sandbox_executions)"
                    ).fetchall()
                ]
                self.assertIn("runtime_preset", sandbox_cols)
                self.assertIn("network_policy", sandbox_cols)
                self.assertIn("stdout", sandbox_cols)
                self.assertIn("stderr", sandbox_cols)
                self.assertIn("output_files_json", sandbox_cols)
                self.assertIn("owner_id", sandbox_cols)
                self.assertIn("tenant_id", sandbox_cols)
                self.assertIn("principal_id", sandbox_cols)
                sandbox_event_cols = [
                    r[1]
                    for r in conn.execute(
                        "PRAGMA table_info(code_sandbox_execution_events)"
                    ).fetchall()
                ]
                self.assertIn("execution_id", sandbox_event_cols)
                self.assertIn("seq", sandbox_event_cols)
                self.assertIn("event_type", sandbox_event_cols)
                self.assertIn("metadata_json", sandbox_event_cols)
            finally:
                conn.close()

    def test_legacy_database_without_schema_migrations_table(self) -> None:
        """Pre–Phase 13 DB: core tables only; runner applies tracking + additive columns."""
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db_path = Path(tmp) / "legacy.db"
            conn = sqlite3.connect(db_path)
            try:
                conn.executescript(
                    """
                    CREATE TABLE conversations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        created_at TEXT NOT NULL,
                        ip TEXT NOT NULL,
                        model TEXT NOT NULL,
                        turn_count INTEGER NOT NULL,
                        user_message TEXT NOT NULL,
                        assistant_response TEXT NOT NULL,
                        response_ms INTEGER
                    );
                    CREATE TABLE sessions (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL DEFAULT '',
                        model TEXT NOT NULL DEFAULT '',
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        messages TEXT NOT NULL DEFAULT '[]'
                    );
                    """
                )
                conn.commit()
            finally:
                conn.close()

            apply_migrations(db_path)
            conn = sqlite3.connect(db_path)
            try:
                n = conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
                self.assertEqual(n, 18)
                cols = [
                    r[1]
                    for r in conn.execute("PRAGMA table_info(conversations)").fetchall()
                ]
                self.assertIn("user_name", cols)
                self.assertIn("session_id", cols)
                session_cols = [
                    r[1] for r in conn.execute("PRAGMA table_info(sessions)").fetchall()
                ]
                self.assertIn("schema_version", session_cols)
                self.assertIn("owner_id", session_cols)
                self.assertIn("tenant_id", session_cols)
                self.assertIn("principal_id", session_cols)
                knowledge_cols = [
                    r[1]
                    for r in conn.execute(
                        "PRAGMA table_info(knowledge_documents)"
                    ).fetchall()
                ]
                self.assertIn("storage_path", knowledge_cols)
                self.assertIn("owner_id", knowledge_cols)
                self.assertIn("tenant_id", knowledge_cols)
                self.assertIn("principal_id", knowledge_cols)
                artifact_cols = [
                    r[1]
                    for r in conn.execute(
                        "PRAGMA table_info(chat_artifacts)"
                    ).fetchall()
                ]
                self.assertIn("storage_path", artifact_cols)
                self.assertIn("tenant_id", artifact_cols)
                self.assertIn("principal_id", artifact_cols)
                media_cols = [
                    r[1]
                    for r in conn.execute("PRAGMA table_info(media_uploads)").fetchall()
                ]
                self.assertIn("tenant_id", media_cols)
                self.assertIn("principal_id", media_cols)
                workbench_cols = [
                    r[1]
                    for r in conn.execute(
                        "PRAGMA table_info(workbench_tasks)"
                    ).fetchall()
                ]
                self.assertIn("status", workbench_cols)
                self.assertIn("prompt", workbench_cols)
                self.assertIn("knowledge_document_ids", workbench_cols)
                self.assertIn("connector_ids", workbench_cols)
                self.assertIn("source_ids", workbench_cols)
                self.assertIn("owner_id", workbench_cols)
                self.assertIn("tenant_id", workbench_cols)
                self.assertIn("principal_id", workbench_cols)
                self.assertIn("result_text", workbench_cols)
                self.assertIn("result_citations_json", workbench_cols)
                self.assertIn("auth_scopes_json", workbench_cols)
                self.assertIn("credential_id", workbench_cols)
                self.assertIn("auth_mode", workbench_cols)
                workbench_event_cols = [
                    r[1]
                    for r in conn.execute(
                        "PRAGMA table_info(workbench_task_events)"
                    ).fetchall()
                ]
                self.assertIn("task_id", workbench_event_cols)
                self.assertIn("seq", workbench_event_cols)
                self.assertIn("event_type", workbench_event_cols)
                self.assertIn("metadata_json", workbench_event_cols)
                sandbox_cols = [
                    r[1]
                    for r in conn.execute(
                        "PRAGMA table_info(code_sandbox_executions)"
                    ).fetchall()
                ]
                self.assertIn("runtime_preset", sandbox_cols)
                self.assertIn("network_policy", sandbox_cols)
                self.assertIn("stdout", sandbox_cols)
                self.assertIn("stderr", sandbox_cols)
                self.assertIn("output_files_json", sandbox_cols)
                sandbox_event_cols = [
                    r[1]
                    for r in conn.execute(
                        "PRAGMA table_info(code_sandbox_execution_events)"
                    ).fetchall()
                ]
                self.assertIn("execution_id", sandbox_event_cols)
                self.assertIn("seq", sandbox_event_cols)
                self.assertIn("event_type", sandbox_event_cols)
                self.assertIn("metadata_json", sandbox_event_cols)
            finally:
                conn.close()

    def test_checksum_mismatch_raises(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            base = Path(tmp)
            mig = base / "migrations"
            shutil.copytree(_REPO_MIGRATIONS, mig)
            db_path = base / "t.db"
            with patch("backend.services.db_migrations._MIGRATIONS_DIR", mig):
                apply_migrations(db_path)
            tampered = mig / "004_add_conversations_session_id.sql"
            tampered.write_text(
                tampered.read_text(encoding="utf-8") + "\n-- tamper\n", encoding="utf-8"
            )
            with patch("backend.services.db_migrations._MIGRATIONS_DIR", mig):
                with self.assertRaises(RuntimeError) as ctx:
                    apply_migrations(db_path)
            self.assertIn("checksum", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
