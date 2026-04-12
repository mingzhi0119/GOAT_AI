"""Phase 15.10 — Session history integration tests.

Seeds SQLite directly via log_service, then exercises the history API
(GET list, GET detail, DELETE single, DELETE all) through the full
FastAPI TestClient stack. No live Ollama required.
"""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import patch

from backend.api_errors import INTERNAL_ERROR, REQUEST_VALIDATION_ERROR
from backend.services.exceptions import PersistenceWriteError

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
    from backend.platform.config import get_settings

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
    from backend.platform.config import get_settings

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
    from backend.platform.config import get_settings

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


def test_rename_history_session_updates_title(app_client: object) -> None:
    from fastapi.testclient import TestClient
    from backend.platform.config import get_settings

    assert isinstance(app_client, TestClient)
    settings = get_settings()
    db = settings.log_db_path

    from backend.services import log_service

    log_service.init_db(db)
    _seed_session(db, "sess-rename-1", "Original Title")

    response = app_client.patch(
        "/api/history/sess-rename-1",
        json={"title": "Renamed Title"},
    )
    assert response.status_code == 204

    detail = app_client.get("/api/history/sess-rename-1")
    assert detail.status_code == 200
    assert detail.json()["title"] == "Renamed Title"


def test_rename_history_session_rejects_whitespace_only_title(
    app_client: object,
) -> None:
    from fastapi.testclient import TestClient
    from backend.platform.config import get_settings

    assert isinstance(app_client, TestClient)
    settings = get_settings()
    db = settings.log_db_path

    from backend.services import log_service

    log_service.init_db(db)
    _seed_session(db, "sess-rename-empty", "Original Title")

    response = app_client.patch(
        "/api/history/sess-rename-empty",
        json={"title": "   "},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == "Title cannot be empty"
    assert body["code"] == REQUEST_VALIDATION_ERROR


def test_rename_history_session_returns_500_on_persistence_failure(
    integration_env: None,
) -> None:
    from fastapi.testclient import TestClient
    from backend.platform.config import get_settings
    from backend.main import create_app

    settings = get_settings()
    db = settings.log_db_path

    from backend.services import log_service

    log_service.init_db(db)
    _seed_session(db, "sess-rename-fail", "Original Title")

    with TestClient(create_app(), raise_server_exceptions=False) as client:
        with patch(
            "backend.services.log_service.rename_session_title",
            side_effect=PersistenceWriteError("db down"),
        ):
            response = client.patch(
                "/api/history/sess-rename-fail",
                json={"title": "Renamed Title"},
            )

    assert response.status_code == 500
    assert response.json()["code"] == INTERNAL_ERROR


# ── delete all ────────────────────────────────────────────────────────────────


def test_delete_all_history_removes_all(app_client: object) -> None:
    from fastapi.testclient import TestClient
    from backend.platform.config import get_settings

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


def test_delete_all_history_returns_500_on_persistence_failure(
    integration_env: None,
) -> None:
    from fastapi.testclient import TestClient
    from backend.main import create_app

    with TestClient(create_app(), raise_server_exceptions=False) as client:
        with patch(
            "backend.services.log_service.delete_all_sessions",
            side_effect=PersistenceWriteError("db down"),
        ):
            response = client.delete("/api/history")

    assert response.status_code == 500
    assert response.json()["code"] == INTERNAL_ERROR
