from __future__ import annotations

import unittest
from pathlib import Path

from goat_ai.config.settings import Settings
from goat_ai.runtime.runtime_target import (
    current_runtime_target,
    ordered_runtime_targets,
)


def make_settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "ollama_base_url": "http://127.0.0.1:11434",
        "generate_timeout": 120,
        "max_upload_mb": 20,
        "max_upload_bytes": 20 * 1024 * 1024,
        "max_dataframe_rows": 50000,
        "use_chat_api": True,
        "system_prompt": "test prompt",
        "app_root": Path("."),
        "logo_svg": Path("logo.svg"),
        "log_db_path": Path("chat_logs.db"),
        "api_key": "",
        "rate_limit_window_sec": 60,
        "rate_limit_max_requests": 60,
        "deploy_target": "auto",
        "server_port": 62606,
        "local_port": 62606,
        "gpu_target_uuid": "",
        "gpu_target_index": 0,
        "latency_rolling_max_samples": 20,
    }
    defaults.update(overrides)
    return Settings(**defaults)


class RuntimeTargetTests(unittest.TestCase):
    def test_auto_returns_server_only_when_server_port_is_bindable(self) -> None:
        settings = make_settings()

        targets = ordered_runtime_targets(
            settings,
            probe=lambda _host, _port: (True, "bind check passed"),
        )

        self.assertEqual([item.port for item in targets], [62606])
        self.assertEqual(targets[0].mode, "server62606")

    def test_auto_keeps_server_only_when_server_port_is_unavailable(self) -> None:
        settings = make_settings()

        targets = ordered_runtime_targets(
            settings,
            probe=lambda _host, _port: (False, "address already in use"),
        )

        self.assertEqual([item.port for item in targets], [62606])
        self.assertEqual(targets[0].mode, "server62606")
        self.assertIn("address already in use", targets[0].reason)

    def test_explicit_server_mode_returns_only_server_port(self) -> None:
        settings = make_settings(deploy_target="server")

        targets = ordered_runtime_targets(settings)

        self.assertEqual([item.port for item in targets], [62606])
        self.assertEqual(targets[0].mode, "server62606")

    def test_explicit_local_mode_is_deprecated_and_returns_server_port(self) -> None:
        settings = make_settings(deploy_target="local")

        targets = ordered_runtime_targets(settings)

        self.assertEqual([item.port for item in targets], [62606])
        self.assertEqual(targets[0].mode, "server62606")
        self.assertIn("deprecated", targets[0].reason)

    def test_current_runtime_target_describes_server_port(self) -> None:
        settings = make_settings()

        target = current_runtime_target(settings, current_port=62606)

        self.assertEqual(target.mode, "server62606")
        self.assertEqual(target.base_url, "http://127.0.0.1:62606")

    def test_current_runtime_target_marks_custom_port_as_override(self) -> None:
        settings = make_settings()

        target = current_runtime_target(settings, current_port=9000)

        self.assertEqual(target.mode, "explicit_override")
        self.assertEqual(target.base_url, "http://127.0.0.1:9000")


if __name__ == "__main__":
    unittest.main()
