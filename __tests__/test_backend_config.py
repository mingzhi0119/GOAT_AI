from __future__ import annotations

import importlib
import os

import backend.config as backend_config


def _restore_env(name: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value


def test_backend_port_defaults_to_62606() -> None:
    original_server_port = os.environ.get("GOAT_SERVER_PORT")
    original_legacy_port = os.environ.get("GOAT_PORT")
    try:
        os.environ.pop("GOAT_SERVER_PORT", None)
        os.environ.pop("GOAT_PORT", None)
        importlib.reload(backend_config)
        assert backend_config.BACKEND_PORT == 62606
    finally:
        _restore_env("GOAT_SERVER_PORT", original_server_port)
        _restore_env("GOAT_PORT", original_legacy_port)
        importlib.reload(backend_config)


def test_backend_port_prefers_goat_server_port_over_legacy_goat_port() -> None:
    original_server_port = os.environ.get("GOAT_SERVER_PORT")
    original_legacy_port = os.environ.get("GOAT_PORT")
    try:
        os.environ["GOAT_SERVER_PORT"] = "62606"
        os.environ["GOAT_PORT"] = "9001"
        importlib.reload(backend_config)
        assert backend_config.BACKEND_PORT == 62606
    finally:
        _restore_env("GOAT_SERVER_PORT", original_server_port)
        _restore_env("GOAT_PORT", original_legacy_port)
        importlib.reload(backend_config)
