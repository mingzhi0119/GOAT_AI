"""Shared fixtures for integration tests (temp SQLite paths, TestClient)."""

from __future__ import annotations

import importlib

import pytest


def _clear_imported_settings_caches() -> None:
    import backend.config as backend_config
    import backend.dependencies as backend_dependencies
    import backend.http_security as backend_http_security
    import backend.main as backend_main
    from backend.routers import (
        artifacts,
        chat,
        code_sandbox,
        history,
        knowledge,
        media,
        models,
        system,
        upload,
        workbench,
    )

    backend_config.get_settings.cache_clear()
    backend_dependencies.get_settings.cache_clear()
    backend_http_security.get_settings.cache_clear()
    backend_main.get_settings.cache_clear()

    # Some tests reload backend.config, so route modules can hold stale get_settings aliases.
    for module in (
        artifacts,
        chat,
        code_sandbox,
        history,
        knowledge,
        media,
        models,
        system,
        upload,
        workbench,
    ):
        importlib.reload(module)


@pytest.fixture
def integration_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """Point GOAT SQLite paths at an isolated temp dir and skip Ollama readiness probe."""
    base = tmp_path_factory.mktemp("goat_integration")
    log_db = base / "chat_logs.db"
    data_dir = base / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("GOAT_API_KEY", "")
    monkeypatch.setenv("GOAT_API_KEY_WRITE", "")
    monkeypatch.setenv("GOAT_API_CREDENTIALS_JSON", "")
    monkeypatch.setenv("GOAT_REQUIRE_SESSION_OWNER", "false")
    monkeypatch.setenv("GOAT_LOG_PATH", str(log_db))
    monkeypatch.setenv("GOAT_DATA_DIR", str(data_dir))
    monkeypatch.setenv("GOAT_READY_SKIP_OLLAMA_PROBE", "true")
    _clear_imported_settings_caches()
    yield
    _clear_imported_settings_caches()


@pytest.fixture
def app_client(integration_env: None) -> object:
    """FastAPI TestClient against ``create_app()`` with integration env applied."""
    from fastapi.testclient import TestClient

    from backend.main import create_app

    with TestClient(create_app()) as client:
        yield client
