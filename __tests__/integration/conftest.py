"""Shared fixtures for integration tests (temp SQLite paths, TestClient)."""

from __future__ import annotations

import pytest

from backend.config import get_settings


@pytest.fixture
def integration_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """Point GOAT SQLite paths at an isolated temp dir and skip Ollama readiness probe."""
    base = tmp_path_factory.mktemp("goat_integration")
    log_db = base / "chat_logs.db"
    data_dir = base / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("GOAT_LOG_PATH", str(log_db))
    monkeypatch.setenv("GOAT_DATA_DIR", str(data_dir))
    monkeypatch.setenv("GOAT_READY_SKIP_OLLAMA_PROBE", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def app_client(integration_env: None) -> object:
    """FastAPI TestClient against ``create_app()`` with integration env applied."""
    from fastapi.testclient import TestClient

    from backend.main import create_app

    with TestClient(create_app()) as client:
        yield client
