"""Phase 15.10 — Session history integration tests.

Seeds SQLite directly via log_service, then exercises the history API
(GET list, GET detail, DELETE single, DELETE all) through the full
FastAPI TestClient stack. No live Ollama required.
"""

from __future__ import annotations

import pytest
from pathlib import Path

pytestmark = pytest.mark.integration

# ── helpers ───────────────────────────────────────────────────────────────────


def _seed_session(db: Path, session_id: str, title: str, owner_id: str = "") -> None:
    from backend.services import log_service
    from backend.services.session_message_codec import SESSION_PAYLOAD_VERSION

    now = "2026-01-01T00:00:00Z"
    payload = {
        "version": SESSION_PAYLOAD_VERSION,
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ],
        "chart_data_source": "none",
    }
    log_service.upsert_session(
        db_path=db,
        session_id=session_id,
        title=title,
        model="test-model",
        payload=payload,
        created_at=now,
        updated_at=now,
        owner_id=owner_id,
    )


# ── list ──────────────────────────────────────────────────────────────────────


def test_list_history_returns_seeded_sessions(app_client: object) -> None:
    from fastapi.testclient import TestClient
    from backend.config import get_settings

    assert isinstance(app_client, TestClient)
    settings = get_settings()
    db = settings.log_db_path

    from backend.services import log_service

    log_service.init_db(db)
    _seed_session(db, "sess-list-1", "Session One")
    _seed_session(db, "sess-list-2", "Session Two")

    response = app_client.get("/api/history")
    assert response.status_code == 200
    body = response.json()
    ids = {s["id"] for s in body["sessions"]}
    assert "sess-list-1" in ids
    assert "sess-list-2" in ids


# ── detail ────────────────────────────────────────────────────────────────────


def test_get_history_session_detail_returns_messages(app_client: object) -> None:
    from fastapi.testclient import TestClient
    from backend.config import get_settings

    assert isinstance(app_client, TestClient)
    settings = get_settings()
    db = settings.log_db_path

    from backend.services import log_service

    log_service.init_db(db)
    _seed_session(db, "sess-detail-1", "Detail Test")

    response = app_client.get("/api/history/sess-detail-1")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "sess-detail-1"
    assert body["title"] == "Detail Test"
    assert any(m["role"] == "user" for m in body["messages"])
    assert any(m["role"] == "assistant" for m in body["messages"])


def test_get_history_session_detail_not_found(app_client: object) -> None:
    from fastapi.testclient import TestClient

    assert isinstance(app_client, TestClient)
    response = app_client.get("/api/history/no-such-session")
    assert response.status_code == 404


# ── delete single ─────────────────────────────────────────────────────────────


def test_delete_history_session_removes_it(app_client: object) -> None:
    from fastapi.testclient import TestClient
    from backend.config import get_settings

    assert isinstance(app_client, TestClient)
    settings = get_settings()
    db = settings.log_db_path

    from backend.services import log_service

    log_service.init_db(db)
    _seed_session(db, "sess-del-1", "To Delete")

    assert app_client.get("/api/history/sess-del-1").status_code == 200
    assert app_client.delete("/api/history/sess-del-1").status_code == 204
    assert app_client.get("/api/history/sess-del-1").status_code == 404


def test_delete_history_session_not_found(app_client: object) -> None:
    from fastapi.testclient import TestClient

    assert isinstance(app_client, TestClient)
    response = app_client.delete("/api/history/ghost-session")
    assert response.status_code == 404


# ── delete all ────────────────────────────────────────────────────────────────


def test_delete_all_history_removes_all(app_client: object) -> None:
    from fastapi.testclient import TestClient
    from backend.config import get_settings

    assert isinstance(app_client, TestClient)
    settings = get_settings()
    db = settings.log_db_path

    from backend.services import log_service

    log_service.init_db(db)
    _seed_session(db, "sess-all-1", "Alpha")
    _seed_session(db, "sess-all-2", "Beta")

    assert app_client.delete("/api/history").status_code == 204
    body = app_client.get("/api/history").json()
    assert body["sessions"] == []
