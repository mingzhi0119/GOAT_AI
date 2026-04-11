from __future__ import annotations

from pathlib import Path
import os

from goat_ai.desktop_sidecar import configure_desktop_environment


def test_configure_desktop_environment_seeds_runtime_paths(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("GOAT_LOG_PATH", raising=False)
    monkeypatch.delenv("GOAT_DATA_DIR", raising=False)
    monkeypatch.delenv("GOAT_SERVER_PORT", raising=False)
    monkeypatch.delenv("GOAT_LOCAL_PORT", raising=False)
    monkeypatch.delenv("GOAT_DEPLOY_TARGET", raising=False)
    monkeypatch.delenv("GOAT_DESKTOP_APP_DATA_DIR", raising=False)

    resolved = configure_desktop_environment(tmp_path / "desktop-data", 62606)

    assert resolved == (tmp_path / "desktop-data").resolve()
    assert (resolved / "data").is_dir()
    assert os.environ["GOAT_DESKTOP_APP_DATA_DIR"] == str(resolved)
    assert os.environ["GOAT_LOG_PATH"] == str(resolved / "chat_logs.db")
    assert os.environ["GOAT_DATA_DIR"] == str(resolved / "data")
    assert os.environ["GOAT_SERVER_PORT"] == "62606"
    assert os.environ["GOAT_LOCAL_PORT"] == "62606"
    assert os.environ["GOAT_DEPLOY_TARGET"] == "local"


def test_configure_desktop_environment_overrides_inherited_runtime_paths(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("GOAT_DESKTOP_APP_DATA_DIR", "C:/stale/app")
    monkeypatch.setenv("GOAT_LOG_PATH", "C:/stale/chat_logs.db")
    monkeypatch.setenv("GOAT_DATA_DIR", "C:/stale/data")
    monkeypatch.setenv("GOAT_SERVER_PORT", "9999")
    monkeypatch.setenv("GOAT_LOCAL_PORT", "9999")
    monkeypatch.setenv("GOAT_DEPLOY_TARGET", "remote")

    resolved = configure_desktop_environment(tmp_path / "desktop-data", 62616)

    assert os.environ["GOAT_DESKTOP_APP_DATA_DIR"] == str(resolved)
    assert os.environ["GOAT_LOG_PATH"] == str(resolved / "chat_logs.db")
    assert os.environ["GOAT_DATA_DIR"] == str(resolved / "data")
    assert os.environ["GOAT_SERVER_PORT"] == "62616"
    assert os.environ["GOAT_LOCAL_PORT"] == "62616"
    assert os.environ["GOAT_DEPLOY_TARGET"] == "local"
