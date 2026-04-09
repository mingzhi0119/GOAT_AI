from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from backend.services import log_service


class LogServiceWaveATests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = Path(self.tmpdir.name) / "t.db"
        log_service.init_db(self.db_path)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    @patch("backend.services.log_service.inc_sqlite_log_write_failure")
    def test_log_conversation_failure_calls_metric(self, inc_mock: MagicMock) -> None:
        with patch("sqlite3.connect", side_effect=sqlite3.Error("injected")):
            log_service.log_conversation(
                db_path=self.db_path,
                ip="127.0.0.1",
                model="m",
                turn_count=1,
                user_message="hi",
                assistant_response="yo",
                response_ms=1,
            )
        inc_mock.assert_called_once_with(
            operation="conversation", code="SQLITE_WRITE_FAILED"
        )

    @patch("backend.services.log_service.inc_sqlite_log_write_failure")
    def test_upsert_session_failure_calls_metric(self, inc_mock: MagicMock) -> None:
        with patch("sqlite3.connect", side_effect=sqlite3.Error("injected")):
            log_service.upsert_session(
                db_path=self.db_path,
                session_id="s1",
                title="t",
                model="m",
                payload={"messages": []},
                created_at="2020-01-01T00:00:00+00:00",
                updated_at="2020-01-01T00:00:00+00:00",
            )
        inc_mock.assert_called_once_with(
            operation="session_upsert", code="SQLITE_WRITE_FAILED"
        )


if __name__ == "__main__":
    unittest.main()
