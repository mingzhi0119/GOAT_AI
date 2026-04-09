"""In-memory SessionRepository — no SQLite file; validates payload decode round-trip."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from backend.models.chat import ChatMessage
from backend.services.artifact_service import PersistedArtifactRecord
from backend.services.chat_runtime import (
    SessionDetailRecord,
    SessionRepository,
    SessionSummaryRecord,
    SessionUpsertPayload,
)
from backend.services.session_message_codec import (
    SESSION_PAYLOAD_VERSION,
    build_session_payload,
    decode_session_payload,
)


class InMemorySessionRepository:
    """Minimal dict-backed repository implementing SessionRepository."""

    def __init__(self) -> None:
        self._rows: dict[str, dict[str, object]] = {}
        self._artifacts: dict[str, PersistedArtifactRecord] = {}

    def list_sessions(
        self, owner_filter: str | None = None
    ) -> list[SessionSummaryRecord]:
        out: list[SessionSummaryRecord] = []
        for sid, row in sorted(
            self._rows.items(), key=lambda kv: str(kv[1].get("updated_at", ""))
        ):
            row_owner = str(row.get("owner_id", ""))
            if owner_filter is not None and row_owner != owner_filter:
                continue
            out.append(
                SessionSummaryRecord(
                    id=sid,
                    title=str(row["title"]),
                    model=str(row["model"]),
                    schema_version=int(row.get("schema_version", 1)),
                    created_at=str(row["created_at"]),
                    updated_at=str(row["updated_at"]),
                    owner_id=row_owner,
                )
            )
        return out

    def get_session(self, session_id: str) -> SessionDetailRecord | None:
        row = self._rows.get(session_id)
        if row is None:
            return None
        raw_messages = row.get("messages", [])
        decoded = decode_session_payload(
            raw_messages if isinstance(raw_messages, (list, dict)) else []
        )
        return SessionDetailRecord(
            id=str(row["id"]),
            title=str(row["title"]),
            model=str(row["model"]),
            schema_version=int(row.get("schema_version", 1)),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            owner_id=str(row.get("owner_id", "")),
            messages=decoded.messages,
            chart_spec=decoded.chart_spec,
            file_context_prompt=decoded.file_context_prompt,
            knowledge_documents=decoded.knowledge_documents,
            chart_data_source=decoded.chart_data_source,
        )

    def upsert_session(self, payload: SessionUpsertPayload) -> None:
        self._rows[payload.session_id] = {
            "id": payload.session_id,
            "title": payload.title,
            "model": payload.model,
            "schema_version": payload.schema_version,
            "created_at": payload.created_at,
            "updated_at": payload.updated_at,
            "messages": payload.payload,
            "owner_id": payload.owner_id,
        }

    def delete_session(self, session_id: str) -> None:
        self._rows.pop(session_id, None)

    def delete_all_sessions(self, owner_filter: str | None = None) -> None:
        if owner_filter is None:
            self._rows.clear()
            return
        for sid in [
            k
            for k, row in self._rows.items()
            if str(row.get("owner_id", "")) == owner_filter
        ]:
            del self._rows[sid]

    def create_chat_artifact(self, record: PersistedArtifactRecord) -> None:
        self._artifacts[record.id] = record

    def get_chat_artifact(self, artifact_id: str) -> PersistedArtifactRecord | None:
        return self._artifacts.get(artifact_id)


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
