from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend.services import log_service


class LogServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = Path(self.tmpdir.name) / "chat_logs.db"
        log_service.init_db(self.db_path)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_session_crud_and_conversation_link(self) -> None:
        session_id = "session-1"
        log_service.upsert_session(
            db_path=self.db_path,
            session_id=session_id,
            title="First chat",
            model="llama3:latest",
            messages=[{"role": "user", "content": "hello"}],
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:01+00:00",
        )

        sessions = log_service.list_sessions(db_path=self.db_path)
        self.assertEqual(1, len(sessions))
        self.assertEqual(session_id, sessions[0]["id"])

        detail = log_service.get_session(db_path=self.db_path, session_id=session_id)
        self.assertIsNotNone(detail)
        assert detail is not None
        self.assertEqual("First chat", detail["title"])
        self.assertEqual([{"role": "user", "content": "hello"}], detail["messages"])

        log_service.log_conversation(
            db_path=self.db_path,
            ip="127.0.0.1",
            model="llama3:latest",
            turn_count=1,
            user_message="hello",
            assistant_response="world",
            response_ms=12,
            user_name="Simon",
            session_id=session_id,
        )

        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT session_id FROM conversations ORDER BY id DESC LIMIT 1"
            ).fetchone()
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(session_id, row[0])

        log_service.delete_session(db_path=self.db_path, session_id=session_id)
        self.assertIsNone(log_service.get_session(db_path=self.db_path, session_id=session_id))

        with sqlite3.connect(self.db_path) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM conversations WHERE session_id = ?",
                (session_id,),
            ).fetchone()[0]
        # Sidebar delete removes ``sessions`` only; per-turn audit rows stay.
        self.assertEqual(1, count)


if __name__ == "__main__":
    unittest.main()
