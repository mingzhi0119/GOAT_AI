from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import goat_ai.config.settings as config


class DotenvConfigTests(unittest.TestCase):
    def test_load_dotenv_file_sets_missing_values_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dotenv_path = Path(tmp) / ".env"
            dotenv_path.write_text(
                "\n".join(
                    [
                        "# comment",
                        "OLLAMA_BASE_URL=http://127.0.0.1:11435",
                        "QUOTED_VALUE='hello world'",
                        'DOUBLE_QUOTED="hello again"',
                    ]
                ),
                encoding="utf-8",
            )

            original = {
                "OLLAMA_BASE_URL": os.environ.get("OLLAMA_BASE_URL"),
                "QUOTED_VALUE": os.environ.get("QUOTED_VALUE"),
                "DOUBLE_QUOTED": os.environ.get("DOUBLE_QUOTED"),
            }
            try:
                os.environ["OLLAMA_BASE_URL"] = "http://127.0.0.1:9999"
                os.environ.pop("QUOTED_VALUE", None)
                os.environ.pop("DOUBLE_QUOTED", None)

                config._load_dotenv_file(dotenv_path)

                self.assertEqual(os.environ["OLLAMA_BASE_URL"], "http://127.0.0.1:9999")
                self.assertEqual(os.environ["QUOTED_VALUE"], "hello world")
                self.assertEqual(os.environ["DOUBLE_QUOTED"], "hello again")
            finally:
                for key, value in original.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value

    def test_load_settings_rejects_invalid_deploy_target(self) -> None:
        original = os.environ.get("GOAT_DEPLOY_TARGET")
        try:
            os.environ["GOAT_DEPLOY_TARGET"] = "invalid"
            with self.assertRaises(ValueError):
                config.load_settings()
        finally:
            if original is None:
                os.environ.pop("GOAT_DEPLOY_TARGET", None)
            else:
                os.environ["GOAT_DEPLOY_TARGET"] = original

    def test_load_settings_defaults_runtime_paths_to_var(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app_root = Path(tmp)
            runtime_root = app_root / "var"
            original_env = _capture_env(
                "GOAT_RUNTIME_ROOT",
                "GOAT_LOG_DIR",
                "GOAT_LOG_PATH",
                "GOAT_DATA_DIR",
            )
            try:
                _clear_env(*original_env.keys())
                with (
                    patch.object(config, "APP_ROOT", app_root),
                    patch.object(config, "DEFAULT_RUNTIME_ROOT", runtime_root),
                ):
                    settings = config.load_settings()
                self.assertEqual(settings.runtime_root, runtime_root)
                self.assertEqual(settings.log_dir, runtime_root / "logs")
                self.assertEqual(settings.log_db_path, runtime_root / "chat_logs.db")
                self.assertEqual(settings.data_dir, runtime_root / "data")
                self.assertTrue((runtime_root / "logs").is_dir())
                self.assertTrue((runtime_root / "data").is_dir())
            finally:
                _restore_many(original_env)

    def test_load_settings_migrates_legacy_runtime_state_into_var(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app_root = Path(tmp)
            runtime_root = app_root / "var"
            legacy_db = app_root / "chat_logs.db"
            legacy_logs = app_root / "logs" / "fastapi.log"
            legacy_data = app_root / "data" / "upload.txt"
            legacy_db.write_text("db-bytes", encoding="utf-8")
            legacy_logs.parent.mkdir(parents=True, exist_ok=True)
            legacy_logs.write_text("log-bytes", encoding="utf-8")
            legacy_data.parent.mkdir(parents=True, exist_ok=True)
            legacy_data.write_text("data-bytes", encoding="utf-8")

            original_env = _capture_env(
                "GOAT_RUNTIME_ROOT",
                "GOAT_LOG_DIR",
                "GOAT_LOG_PATH",
                "GOAT_DATA_DIR",
            )
            try:
                _clear_env(*original_env.keys())
                with (
                    patch.object(config, "APP_ROOT", app_root),
                    patch.object(config, "DEFAULT_RUNTIME_ROOT", runtime_root),
                ):
                    settings = config.load_settings()
                self.assertEqual(settings.runtime_root, runtime_root)
                self.assertEqual(
                    (runtime_root / "chat_logs.db").read_text(encoding="utf-8"),
                    "db-bytes",
                )
                self.assertEqual(
                    (runtime_root / "logs" / "fastapi.log").read_text(encoding="utf-8"),
                    "log-bytes",
                )
                self.assertEqual(
                    (runtime_root / "data" / "upload.txt").read_text(encoding="utf-8"),
                    "data-bytes",
                )
                self.assertTrue(legacy_db.is_file())
                self.assertTrue(legacy_logs.is_file())
                self.assertTrue(legacy_data.is_file())
            finally:
                _restore_many(original_env)

    def test_load_settings_parses_workbench_web_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app_root = Path(tmp)
            runtime_root = app_root / "var"
            original_env = _capture_env(
                "GOAT_WORKBENCH_WEB_PROVIDER",
                "GOAT_WORKBENCH_WEB_MAX_RESULTS",
                "GOAT_WORKBENCH_WEB_TIMEOUT_SEC",
                "GOAT_WORKBENCH_WEB_REGION",
                "GOAT_WORKBENCH_WEB_SAFESEARCH",
            )
            try:
                _clear_env(*original_env.keys())
                os.environ["GOAT_WORKBENCH_WEB_PROVIDER"] = "duckduckgo"
                os.environ["GOAT_WORKBENCH_WEB_MAX_RESULTS"] = "7"
                os.environ["GOAT_WORKBENCH_WEB_TIMEOUT_SEC"] = "11"
                os.environ["GOAT_WORKBENCH_WEB_REGION"] = "us-en"
                os.environ["GOAT_WORKBENCH_WEB_SAFESEARCH"] = "off"
                with (
                    patch.object(config, "APP_ROOT", app_root),
                    patch.object(config, "DEFAULT_RUNTIME_ROOT", runtime_root),
                ):
                    settings = config.load_settings()
                self.assertEqual("duckduckgo", settings.workbench_web_provider)
                self.assertEqual(7, settings.workbench_web_max_results)
                self.assertEqual(11, settings.workbench_web_timeout_sec)
                self.assertEqual("us-en", settings.workbench_web_region)
                self.assertEqual("off", settings.workbench_web_safesearch)
            finally:
                _restore_many(original_env)


def _capture_env(*names: str) -> dict[str, str | None]:
    return {name: os.environ.get(name) for name in names}


def _clear_env(*names: str) -> None:
    for name in names:
        os.environ.pop(name, None)


def _restore_many(values: dict[str, str | None]) -> None:
    for name, value in values.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value


if __name__ == "__main__":
    unittest.main()
