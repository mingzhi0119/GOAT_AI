"""Integration checks for session_messages dual-write / dual-read (Phase 15.4)."""

from __future__ import annotations

import sqlite3

import pytest

from backend.models.chat import ChatMessage
from backend.services import log_service
from backend.services.session_message_codec import (
    SESSION_PAYLOAD_VERSION,
    build_session_payload,
    decode_session_payload,
)

pytestmark = pytest.mark.integration


def test_upsert_writes_session_messages_and_get_reads_them(
    integration_env: None,
) -> None:
    from backend.platform.config import get_settings

    settings = get_settings()
    log_service.init_db(settings.log_db_path)

    sid = "sess-dual-1"
    ts = "2026-04-09T12:00:00+00:00"
    payload = build_session_payload(
        messages=[ChatMessage(role="user", content="integration_hi")],
        assistant_text="integration_reply",
        chart_spec=None,
    )
    log_service.upsert_session(
        db_path=settings.log_db_path,
        session_id=sid,
        title="Title",
        model="llama",
        schema_version=SESSION_PAYLOAD_VERSION,
        payload=payload,
        created_at=ts,
        updated_at=ts,
    )

    with sqlite3.connect(settings.log_db_path) as conn:
        n = conn.execute(
            "SELECT COUNT(*) FROM session_messages WHERE session_id = ?",
            (sid,),
        ).fetchone()[0]
    assert n == 2

    row = log_service.get_session(db_path=settings.log_db_path, session_id=sid)
    assert row is not None
    decoded = decode_session_payload(row["messages"])
    contents = [m["content"] for m in decoded.messages]
    assert "integration_hi" in contents
    assert "integration_reply" in contents
