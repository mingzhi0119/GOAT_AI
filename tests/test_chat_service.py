"""Unit tests for chat_service session title helpers."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from backend.models.chat import ChatMessage
from backend.services import log_service
from backend.services.chat_service import (
    _build_session_title_fallback,
    _session_title_for_upsert,
)


class ChatServiceTitleTests(unittest.TestCase):
    def test_fallback_truncates_first_user_line(self) -> None:
        long_user = "x" * 100
        t = _build_session_title_fallback(
            [ChatMessage(role="user", content=long_user)],
        )
        self.assertEqual(80, len(t))

    def test_first_exchange_uses_ollama_summary(self) -> None:
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        db_path = Path(tmp.name) / "chat_logs.db"
        log_service.init_db(db_path)
        try:
            mock_resp = MagicMock()
            mock_resp.raise_for_status = lambda: None
            mock_resp.json = lambda: {"response": "Math help: 2+2 explained"}
            with patch("backend.services.chat_service.requests.post", return_value=mock_resp):
                title = _session_title_for_upsert(
                    messages=[ChatMessage(role="user", content="What is 2+2?")],
                    assistant_text="The answer is four.",
                    session_id="sid-1",
                    log_db_path=db_path,
                    ollama_base_url="http://127.0.0.1:11434",
                    generate_timeout=30,
                    model="llama3:latest",
                )
            self.assertEqual("Math help: 2+2 explained", title)
        finally:
            tmp.cleanup()

    def test_subsequent_turn_keeps_existing_title(self) -> None:
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        db_path = Path(tmp.name) / "chat_logs.db"
        log_service.init_db(db_path)
        try:
            log_service.upsert_session(
                db_path=db_path,
                session_id="sid-2",
                title="Kept title",
                model="m",
                messages=[
                    {"role": "user", "content": "a"},
                    {"role": "assistant", "content": "b"},
                ],
                created_at="2026-01-01T00:00:00+00:00",
                updated_at="2026-01-01T00:00:01+00:00",
            )
            title = _session_title_for_upsert(
                messages=[
                    ChatMessage(role="user", content="a"),
                    ChatMessage(role="assistant", content="b"),
                    ChatMessage(role="user", content="follow-up"),
                ],
                assistant_text="reply",
                session_id="sid-2",
                log_db_path=db_path,
                ollama_base_url="http://127.0.0.1:11434",
                generate_timeout=30,
                model="m",
            )
            self.assertEqual("Kept title", title)
        finally:
            tmp.cleanup()

    def test_first_exchange_empty_ollama_response_falls_back(self) -> None:
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        db_path = Path(tmp.name) / "chat_logs.db"
        log_service.init_db(db_path)
        try:
            mock_resp = MagicMock()
            mock_resp.raise_for_status = lambda: None
            mock_resp.json = lambda: {"response": ""}
            with patch("backend.services.chat_service.requests.post", return_value=mock_resp):
                title = _session_title_for_upsert(
                    messages=[ChatMessage(role="user", content="Hello world")],
                    assistant_text="Hi there",
                    session_id="sid-3",
                    log_db_path=db_path,
                    ollama_base_url="http://127.0.0.1:11434",
                    generate_timeout=30,
                    model="m",
                )
            self.assertEqual("Hello world", title)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
