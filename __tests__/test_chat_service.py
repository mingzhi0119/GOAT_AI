"""Unit tests for session title helpers extracted from chat orchestration."""
from __future__ import annotations

import unittest
from dataclasses import dataclass

from backend.models.chat import ChatMessage
from backend.services.chat_runtime import SessionDetailRecord, SessionUpsertPayload
from backend.services.session_message_codec import decode_session_payload
from backend.services.session_message_codec import (
    FILE_CONTEXT_REPLY,
    STORED_CHART_ROLE,
    STORED_FILE_CONTEXT_ACK_ROLE,
    STORED_FILE_CONTEXT_ROLE,
)
from backend.services.session_service import (
    build_session_title_fallback,
    persist_chat_session,
    session_title_for_upsert,
)


@dataclass
class FakeSessionRepository:
    sessions: dict[str, SessionDetailRecord]

    def get_session(self, session_id: str) -> SessionDetailRecord | None:
        return self.sessions.get(session_id)

    def upsert_session(self, payload: SessionUpsertPayload) -> None:
        decoded = decode_session_payload(payload.payload)
        self.sessions[payload.session_id] = SessionDetailRecord(
            id=payload.session_id,
            title=payload.title,
            model=payload.model,
            schema_version=payload.schema_version,
            created_at=payload.created_at,
            updated_at=payload.updated_at,
            messages=decoded.messages,
            chart_spec=decoded.chart_spec,
            file_context_prompt=decoded.file_context_prompt,
            chart_data_source=decoded.chart_data_source,
        )

    def list_sessions(self) -> list[object]:
        return []

    def delete_session(self, session_id: str) -> None:
        self.sessions.pop(session_id, None)

    def delete_all_sessions(self) -> None:
        self.sessions.clear()


class FakeTitleGenerator:
    def __init__(self, title: str | None) -> None:
        self._title = title

    def generate_title(
        self,
        *,
        model: str,
        user_text: str,
        assistant_text: str,
    ) -> str | None:
        return self._title


class ChatServiceTitleTests(unittest.TestCase):
    def test_fallback_truncates_last_user_line(self) -> None:
        long_user = "x" * 100
        title = build_session_title_fallback(
            [ChatMessage(role="user", content=long_user)],
        )
        self.assertEqual(81, len(title))
        self.assertTrue(title.endswith("…"))

    def test_first_exchange_uses_ollama_summary(self) -> None:
        title = session_title_for_upsert(
            messages=[ChatMessage(role="user", content="What is 2+2?")],
            assistant_text="The answer is four.",
            session_id="sid-1",
            model="llama3:latest",
            session_repository=FakeSessionRepository(sessions={}),
            title_generator=FakeTitleGenerator("Math help: 2+2 explained"),
        )
        self.assertEqual("Math help: 2+2 explained", title)

    def test_subsequent_turn_keeps_existing_title(self) -> None:
        repository = FakeSessionRepository(
            sessions={
                "sid-2": SessionDetailRecord(
                    id="sid-2",
                    title="Kept title",
                    model="m",
                    schema_version=2,
                    created_at="2026-01-01T00:00:00+00:00",
                    updated_at="2026-01-01T00:00:01+00:00",
                    messages=[
                        {"role": "user", "content": "a"},
                        {"role": "assistant", "content": "b"},
                    ],
                )
            }
        )
        title = session_title_for_upsert(
            messages=[
                ChatMessage(role="user", content="a"),
                ChatMessage(role="assistant", content="b"),
                ChatMessage(role="user", content="follow-up"),
            ],
            assistant_text="reply",
            session_id="sid-2",
            model="m",
            session_repository=repository,
            title_generator=FakeTitleGenerator("should not be used"),
        )
        self.assertEqual("Kept title", title)

    def test_first_exchange_empty_ollama_response_falls_back(self) -> None:
        title = session_title_for_upsert(
            messages=[ChatMessage(role="user", content="Hello world")],
            assistant_text="Hi there",
            session_id="sid-3",
            model="m",
            session_repository=FakeSessionRepository(sessions={}),
            title_generator=FakeTitleGenerator(None),
        )
        self.assertEqual("Hello world", title)

    def test_persist_chat_session_writes_versioned_payload(self) -> None:
        repository = FakeSessionRepository(sessions={})
        persist_chat_session(
            session_id="sid-4",
            model="m",
            final_messages=[
                ChatMessage(
                    role="user",
                    content=(
                        "[User uploaded tabular data for analysis]\n\n"
                        "Column names: month, revenue.\n\n"
                        "CHART_DATA_CSV:\n```\nmonth,revenue\nJan,10\n```"
                    ),
                ),
                ChatMessage(role="assistant", content=FILE_CONTEXT_REPLY),
                ChatMessage(role="user", content="Please chart revenue."),
            ],
            assistant_text="Done.",
            chart_spec=None,
            session_repository=repository,
            title_generator=FakeTitleGenerator("Stored title"),
        )

        stored = repository.get_session("sid-4")
        self.assertIsNotNone(stored)
        assert stored is not None
        self.assertEqual("user", stored.messages[0]["role"])
        self.assertEqual("Please chart revenue.", stored.messages[0]["content"])
        self.assertEqual("assistant", stored.messages[1]["role"])
        self.assertEqual("Done.", stored.messages[1]["content"])
        self.assertIsNotNone(stored.file_context_prompt)
        self.assertEqual("uploaded", stored.chart_data_source)

    def test_decode_session_payload_keeps_legacy_storage_compatible(self) -> None:
        decoded = decode_session_payload(
            [
                {"role": STORED_FILE_CONTEXT_ROLE, "content": "legacy prompt"},
                {"role": STORED_FILE_CONTEXT_ACK_ROLE, "content": FILE_CONTEXT_REPLY},
                {"role": "user", "content": "show me a chart"},
                {"role": "assistant", "content": "done"},
                {"role": STORED_CHART_ROLE, "content": '{"type":"bar","title":"Revenue"}'},
            ]
        )

        self.assertEqual("legacy prompt", decoded.file_context_prompt)
        self.assertEqual("show me a chart", decoded.messages[0]["content"])
        self.assertEqual("done", decoded.messages[1]["content"])
        self.assertEqual("Revenue", decoded.chart_spec["title"])
        self.assertEqual("uploaded", decoded.chart_data_source)


if __name__ == "__main__":
    unittest.main()
