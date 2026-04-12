from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

import goat_ai.runtime.desktop_sidecar as subject


def test_configure_desktop_environment_seeds_runtime_paths(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("GOAT_LOG_PATH", raising=False)
    monkeypatch.delenv("GOAT_DATA_DIR", raising=False)
    monkeypatch.delenv("GOAT_RUNTIME_ROOT", raising=False)
    monkeypatch.delenv("GOAT_LOG_DIR", raising=False)
    monkeypatch.delenv("GOAT_SERVER_PORT", raising=False)
    monkeypatch.delenv("GOAT_LOCAL_PORT", raising=False)
    monkeypatch.delenv("GOAT_DEPLOY_TARGET", raising=False)
    monkeypatch.delenv("GOAT_DESKTOP_APP_DATA_DIR", raising=False)

    resolved = subject.configure_desktop_environment(tmp_path / "desktop-data", 62606)

    assert resolved == (tmp_path / "desktop-data").resolve()
    assert (resolved / "data").is_dir()
    assert (resolved / "logs").is_dir()
    assert os.environ["GOAT_DESKTOP_APP_DATA_DIR"] == str(resolved)
    assert os.environ["GOAT_RUNTIME_ROOT"] == str(resolved)
    assert os.environ["GOAT_LOG_DIR"] == str(resolved / "logs")
    assert os.environ["GOAT_LOG_PATH"] == str(resolved / "chat_logs.db")
    assert os.environ["GOAT_DATA_DIR"] == str(resolved / "data")
    assert os.environ["GOAT_SERVER_PORT"] == "62606"
    assert os.environ["GOAT_LOCAL_PORT"] == "62606"
    assert os.environ["GOAT_DEPLOY_TARGET"] == "local"


def test_configure_desktop_environment_overrides_inherited_runtime_paths(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("GOAT_DESKTOP_APP_DATA_DIR", "C:/stale/app")
    monkeypatch.setenv("GOAT_RUNTIME_ROOT", "C:/stale/runtime")
    monkeypatch.setenv("GOAT_LOG_DIR", "C:/stale/logs")
    monkeypatch.setenv("GOAT_LOG_PATH", "C:/stale/chat_logs.db")
    monkeypatch.setenv("GOAT_DATA_DIR", "C:/stale/data")
    monkeypatch.setenv("GOAT_SERVER_PORT", "9999")
    monkeypatch.setenv("GOAT_LOCAL_PORT", "9999")
    monkeypatch.setenv("GOAT_DEPLOY_TARGET", "remote")

    resolved = subject.configure_desktop_environment(tmp_path / "desktop-data", 62616)

    assert os.environ["GOAT_DESKTOP_APP_DATA_DIR"] == str(resolved)
    assert os.environ["GOAT_RUNTIME_ROOT"] == str(resolved)
    assert os.environ["GOAT_LOG_DIR"] == str(resolved / "logs")
    assert os.environ["GOAT_LOG_PATH"] == str(resolved / "chat_logs.db")
    assert os.environ["GOAT_DATA_DIR"] == str(resolved / "data")
    assert os.environ["GOAT_SERVER_PORT"] == "62616"
    assert os.environ["GOAT_LOCAL_PORT"] == "62616"
    assert os.environ["GOAT_DEPLOY_TARGET"] == "local"


def test_default_desktop_data_root_prefers_platform_specific_locations(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(subject.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    monkeypatch.delenv("APPDATA", raising=False)
    assert subject._default_desktop_data_root() == tmp_path / "local" / "GOAT AI"

    monkeypatch.setattr(subject.sys, "platform", "darwin")
    monkeypatch.setattr(subject.Path, "home", lambda: tmp_path)
    assert (
        subject._default_desktop_data_root()
        == tmp_path / "Library" / "Application Support" / "GOAT AI"
    )

    monkeypatch.setattr(subject.sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    assert subject._default_desktop_data_root() == tmp_path / "xdg" / "goat-ai"


def test_main_wires_desktop_environment_and_uvicorn(
    monkeypatch, tmp_path: Path
) -> None:
    parsed = SimpleNamespace(
        host="127.0.0.1",
        port=62606,
        data_root="~/DesktopRoot",
        log_level="debug",
    )
    configured: list[tuple[Path, int]] = []
    uvicorn_calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        subject,
        "_build_parser",
        lambda: _parser_with_namespace(parsed),
    )
    monkeypatch.setattr(
        subject,
        "configure_desktop_environment",
        lambda data_root, port: configured.append((data_root, port)) or data_root,
    )
    monkeypatch.setattr(
        subject.uvicorn,
        "run",
        lambda app, **kwargs: uvicorn_calls.append({"app": app, **kwargs}),
    )
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    subject.main()

    assert configured == [(tmp_path / "DesktopRoot", 62606)]
    assert uvicorn_calls == [
        {
            "app": "backend.main:create_app",
            "factory": True,
            "host": "127.0.0.1",
            "port": 62606,
            "log_level": "debug",
            "access_log": True,
        }
    ]


def test_run_internal_test_scenario_ignores_disabled_or_blank_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(subject.INTERNAL_TEST_FLAG, raising=False)
    monkeypatch.delenv(subject.INTERNAL_TEST_SCENARIO, raising=False)

    subject.run_internal_test_scenario_if_requested()

    monkeypatch.setenv(subject.INTERNAL_TEST_FLAG, "1")
    subject.run_internal_test_scenario_if_requested()


def test_run_internal_test_scenario_exit_before_ready_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(subject.INTERNAL_TEST_FLAG, "1")
    monkeypatch.setenv(subject.INTERNAL_TEST_SCENARIO, "exit_before_ready")

    with pytest.raises(SystemExit, match="exit_before_ready"):
        subject.run_internal_test_scenario_if_requested()


def test_run_internal_test_scenario_hang_before_ready_sleeps_and_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sleeps: list[float] = []
    monkeypatch.setenv(subject.INTERNAL_TEST_FLAG, "1")
    monkeypatch.setenv(subject.INTERNAL_TEST_SCENARIO, "hang_before_ready")
    monkeypatch.setenv(subject.INTERNAL_TEST_HANG_SEC, "1.5")
    monkeypatch.setattr(subject.time, "sleep", lambda seconds: sleeps.append(seconds))

    with pytest.raises(SystemExit, match="hang_before_ready"):
        subject.run_internal_test_scenario_if_requested()

    assert sleeps == [1.5]


def test_run_internal_test_scenario_rejects_unknown_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(subject.INTERNAL_TEST_FLAG, "1")
    monkeypatch.setenv(subject.INTERNAL_TEST_SCENARIO, "unknown")

    with pytest.raises(SystemExit, match="Unsupported"):
        subject.run_internal_test_scenario_if_requested()


def _parser_with_namespace(namespace: SimpleNamespace):
    parser = subject.argparse.ArgumentParser()
    parser.parse_args = lambda: namespace  # type: ignore[method-assign]
    return parser
