from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend.models.chat import ChatMessage
from backend.services import log_service
from backend.services.privacy_cleanup import purge_ownerless_history
from backend.services.session_message_codec import build_session_payload
from goat_ai.config.settings import Settings


def _settings(root: Path) -> Settings:
    return Settings(
        ollama_base_url="http://127.0.0.1:11434",
        generate_timeout=120,
        max_upload_mb=20,
        max_upload_bytes=20 * 1024 * 1024,
        max_dataframe_rows=50000,
        use_chat_api=True,
        system_prompt="test",
        app_root=root,
        logo_svg=root / "logo.svg",
        log_db_path=root / "chat_logs.db",
        data_dir=root / "data",
        object_store_root=root / "object-store",
        ready_skip_ollama_probe=True,
    )


def _seed_session(
    *,
    settings: Settings,
    session_id: str,
    owner_id: str,
) -> None:
    payload = build_session_payload(
        messages=[ChatMessage(role="user", content=f"hello from {session_id}")],
        assistant_text="world",
        chart_spec=None,
        knowledge_documents=None,
        chart_data_source="none",
    )
    log_service.upsert_session(
        db_path=settings.log_db_path,
        session_id=session_id,
        title=f"Session {session_id}",
        model="gemma4:26b",
        schema_version=2,
        payload=payload,
        created_at="2026-04-13T00:00:00+00:00",
        updated_at="2026-04-13T00:00:01+00:00",
        owner_id=owner_id,
    )
    log_service.create_chat_artifact(
        db_path=settings.log_db_path,
        artifact_id=f"art-{session_id}",
        session_id=session_id,
        owner_id=owner_id,
        tenant_id="tenant:default",
        principal_id="principal:test",
        filename=f"{session_id}.md",
        mime_type="text/markdown",
        byte_size=12,
        storage_path=f"artifacts/{session_id}.md",
        storage_key=f"artifacts/{session_id}.md",
        source_message_index=0,
        created_at="2026-04-13T00:00:02+00:00",
    )
    log_service.log_conversation(
        db_path=settings.log_db_path,
        ip="127.0.0.1",
        model="gemma4:26b",
        turn_count=1,
        user_message="hello",
        assistant_response="world",
        response_ms=10,
        session_id=session_id,
    )


class PrivacyCleanupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        root = Path(self.tmpdir.name)
        self.settings = _settings(root)
        log_service.init_db(self.settings.log_db_path)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_purge_ownerless_history_dry_run_reports_matched_sessions(self) -> None:
        _seed_session(settings=self.settings, session_id="anon-1", owner_id="")
        _seed_session(settings=self.settings, session_id="owned-1", owner_id="alice")

        summary = purge_ownerless_history(settings=self.settings, dry_run=True)

        self.assertTrue(summary.dry_run)
        self.assertEqual("sqlite", summary.backend)
        self.assertEqual(["anon-1"], summary.matched_session_ids)

        with sqlite3.connect(self.settings.log_db_path) as conn:
            self.assertEqual(
                2, conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            )

    def test_purge_ownerless_history_removes_linked_rows_only_for_ownerless_sessions(
        self,
    ) -> None:
        _seed_session(settings=self.settings, session_id="anon-1", owner_id="")
        _seed_session(settings=self.settings, session_id="owned-1", owner_id="alice")

        summary = purge_ownerless_history(settings=self.settings, dry_run=False)

        self.assertFalse(summary.dry_run)
        self.assertEqual(["anon-1"], summary.matched_session_ids)
        self.assertEqual(1, summary.sessions_deleted)
        self.assertEqual(2, summary.session_messages_deleted)
        self.assertEqual(1, summary.chat_artifacts_deleted)
        self.assertEqual(1, summary.conversations_deleted)
        with sqlite3.connect(self.settings.log_db_path) as conn:
            self.assertEqual(
                ["owned-1"],
                [
                    row[0]
                    for row in conn.execute(
                        "SELECT id FROM sessions ORDER BY id"
                    ).fetchall()
                ],
            )
            self.assertEqual(
                0,
                conn.execute(
                    "SELECT COUNT(*) FROM session_messages WHERE session_id = 'anon-1'"
                ).fetchone()[0],
            )
            self.assertEqual(
                0,
                conn.execute(
                    "SELECT COUNT(*) FROM chat_artifacts WHERE session_id = 'anon-1'"
                ).fetchone()[0],
            )
            self.assertEqual(
                0,
                conn.execute(
                    "SELECT COUNT(*) FROM conversations WHERE session_id = 'anon-1'"
                ).fetchone()[0],
            )
            self.assertEqual(
                1,
                conn.execute(
                    "SELECT COUNT(*) FROM conversations WHERE session_id = 'owned-1'"
                ).fetchone()[0],
            )


if __name__ == "__main__":
    unittest.main()
