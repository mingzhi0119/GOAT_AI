"""In-memory SessionRepository — no SQLite file; validates payload decode round-trip."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from __tests__.helpers.session_repository import InMemorySessionRepository
from backend.models.chat import ChatMessage
from backend.services.chat_runtime import (
    SessionRepository,
    SessionUpsertPayload,
)
from backend.services.session_message_codec import (
    SESSION_PAYLOAD_VERSION,
    build_session_payload,
    decode_session_payload,
)


class TestFakeSessionRepository(unittest.TestCase):
    def test_upsert_get_round_trip_matches_decode(self) -> None:
        repo: SessionRepository = InMemorySessionRepository()
        sid = "sess-inmem-1"
        ts = datetime(2026, 4, 8, 12, 0, 0, tzinfo=timezone.utc).isoformat()
        user_msg = ChatMessage(role="user", content="Hello")
        payload_dict = build_session_payload(
            messages=[user_msg],
            assistant_text="Hi there",
            chart_spec=None,
            knowledge_documents=None,
            chart_data_source="none",
        )
        self.assertEqual(payload_dict.get("version"), SESSION_PAYLOAD_VERSION)

        repo.upsert_session(
            SessionUpsertPayload(
                session_id=sid,
                title="T",
                model="m1",
                schema_version=SESSION_PAYLOAD_VERSION,
                payload=payload_dict,
                created_at=ts,
                updated_at=ts,
            )
        )
        detail = repo.get_session(sid)
        self.assertIsNotNone(detail)
        assert detail is not None
        decoded = decode_session_payload(payload_dict)
        self.assertEqual(detail.messages, decoded.messages)
        self.assertEqual(
            detail.messages,
            [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"},
            ],
        )

    def test_get_session_raises_on_future_payload_version(self) -> None:
        from backend.services.session_message_codec import SessionSchemaError

        repo = InMemorySessionRepository()
        sid = "sess-future"
        ts = datetime(2026, 4, 8, 12, 0, 0, tzinfo=timezone.utc).isoformat()
        repo._rows[sid] = {
            "id": sid,
            "title": "Future",
            "model": "m1",
            "schema_version": SESSION_PAYLOAD_VERSION + 1,
            "created_at": ts,
            "updated_at": ts,
            "messages": {
                "version": SESSION_PAYLOAD_VERSION + 1,
                "messages": [{"role": "user", "content": "Hello"}],
                "chart_data_source": "none",
            },
            "owner_id": "",
            "tenant_id": "tenant:default",
            "principal_id": "",
        }

        with self.assertRaises(SessionSchemaError):
            repo.get_session(sid)
