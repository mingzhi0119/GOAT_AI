from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import goat_ai.config.settings as config
from backend.services.browser_access_session import hash_shared_access_password


class DotenvConfigTests(unittest.TestCase):
    def test_load_dotenv_file_sets_missing_values_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dotenv_path = Path(tmp) / ".env"
            dotenv_path.write_text(
                "\n".join(
                    [
                        "# comment",
                        "OLLAMA_BASE_URL=http://127.0.0.1:7777",
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

    def test_load_settings_rejects_invalid_runtime_metadata_backend(self) -> None:
        original_env = _capture_env("GOAT_RUNTIME_METADATA_BACKEND")
        try:
            _clear_env(*original_env.keys())
            os.environ["GOAT_RUNTIME_METADATA_BACKEND"] = "mysql"
            with self.assertRaisesRegex(ValueError, "GOAT_RUNTIME_METADATA_BACKEND"):
                config.load_settings()
        finally:
            _restore_many(original_env)

    def test_load_settings_rejects_postgres_runtime_backend_without_dsn(self) -> None:
        original_env = _capture_env(
            "GOAT_RUNTIME_METADATA_BACKEND",
            "GOAT_RUNTIME_POSTGRES_DSN",
            "GOAT_DEPLOY_TARGET",
        )
        try:
            _clear_env(*original_env.keys())
            os.environ["GOAT_RUNTIME_METADATA_BACKEND"] = "postgres"
            os.environ["GOAT_DEPLOY_TARGET"] = "server"
            with self.assertRaisesRegex(ValueError, "GOAT_RUNTIME_POSTGRES_DSN"):
                config.load_settings()
        finally:
            _restore_many(original_env)

    def test_load_settings_rejects_postgres_runtime_backend_without_server_target(
        self,
    ) -> None:
        original_env = _capture_env(
            "GOAT_RUNTIME_METADATA_BACKEND",
            "GOAT_RUNTIME_POSTGRES_DSN",
            "GOAT_DEPLOY_TARGET",
        )
        try:
            _clear_env(*original_env.keys())
            os.environ["GOAT_RUNTIME_METADATA_BACKEND"] = "postgres"
            os.environ["GOAT_RUNTIME_POSTGRES_DSN"] = (
                "postgresql://goat:secret@db.example.com:5432/goat"
            )
            with self.assertRaisesRegex(ValueError, "GOAT_DEPLOY_TARGET=server"):
                config.load_settings()
        finally:
            _restore_many(original_env)

    def test_load_settings_parses_postgres_runtime_backend_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app_root = Path(tmp)
            runtime_root = app_root / "var"
            original_env = _capture_env(
                "GOAT_RUNTIME_METADATA_BACKEND",
                "GOAT_RUNTIME_POSTGRES_DSN",
                "GOAT_DEPLOY_TARGET",
            )
            try:
                _clear_env(*original_env.keys())
                os.environ["GOAT_RUNTIME_METADATA_BACKEND"] = "postgres"
                os.environ["GOAT_RUNTIME_POSTGRES_DSN"] = (
                    "postgresql://goat:secret@db.example.com:5432/goat"
                )
                os.environ["GOAT_DEPLOY_TARGET"] = "server"
                with (
                    patch.object(config, "APP_ROOT", app_root),
                    patch.object(config, "DEFAULT_RUNTIME_ROOT", runtime_root),
                ):
                    settings = config.load_settings()
                self.assertEqual("postgres", settings.runtime_metadata_backend)
                self.assertEqual(
                    "postgresql://goat:secret@db.example.com:5432/goat",
                    settings.runtime_postgres_dsn,
                )
            finally:
                _restore_many(original_env)

    def test_load_settings_rejects_s3_backend_without_bucket(self) -> None:
        original_env = _capture_env(
            "GOAT_OBJECT_STORE_BACKEND", "GOAT_OBJECT_STORE_BUCKET"
        )
        try:
            _clear_env(*original_env.keys())
            os.environ["GOAT_OBJECT_STORE_BACKEND"] = "s3"
            with self.assertRaisesRegex(ValueError, "GOAT_OBJECT_STORE_BUCKET"):
                config.load_settings()
        finally:
            _restore_many(original_env)

    def test_load_settings_parses_s3_object_store_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app_root = Path(tmp)
            runtime_root = app_root / "var"
            original_env = _capture_env(
                "GOAT_OBJECT_STORE_BACKEND",
                "GOAT_OBJECT_STORE_BUCKET",
                "GOAT_OBJECT_STORE_PREFIX",
                "GOAT_OBJECT_STORE_ENDPOINT_URL",
                "GOAT_OBJECT_STORE_REGION",
                "GOAT_OBJECT_STORE_ACCESS_KEY_ID",
                "GOAT_OBJECT_STORE_SECRET_ACCESS_KEY",
                "GOAT_OBJECT_STORE_S3_ADDRESSING_STYLE",
            )
            try:
                _clear_env(*original_env.keys())
                os.environ["GOAT_OBJECT_STORE_BACKEND"] = "s3"
                os.environ["GOAT_OBJECT_STORE_BUCKET"] = "goat-artifacts"
                os.environ["GOAT_OBJECT_STORE_PREFIX"] = "tenant-a/runtime"
                os.environ["GOAT_OBJECT_STORE_ENDPOINT_URL"] = "http://127.0.0.1:9000"
                os.environ["GOAT_OBJECT_STORE_REGION"] = "us-east-1"
                os.environ["GOAT_OBJECT_STORE_ACCESS_KEY_ID"] = "minio"
                os.environ["GOAT_OBJECT_STORE_SECRET_ACCESS_KEY"] = "secret"
                os.environ["GOAT_OBJECT_STORE_S3_ADDRESSING_STYLE"] = "path"
                with (
                    patch.object(config, "APP_ROOT", app_root),
                    patch.object(config, "DEFAULT_RUNTIME_ROOT", runtime_root),
                ):
                    settings = config.load_settings()
                self.assertEqual("s3", settings.object_store_backend)
                self.assertEqual("goat-artifacts", settings.object_store_bucket)
                self.assertEqual("tenant-a/runtime", settings.object_store_prefix)
                self.assertEqual(
                    "http://127.0.0.1:9000",
                    settings.object_store_endpoint_url,
                )
                self.assertEqual("us-east-1", settings.object_store_region)
                self.assertEqual("minio", settings.object_store_access_key_id)
                self.assertEqual("secret", settings.object_store_secret_access_key)
                self.assertEqual("path", settings.object_store_s3_addressing_style)
            finally:
                _restore_many(original_env)

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
                self.assertEqual("sqlite", settings.runtime_metadata_backend)
                self.assertEqual("", settings.runtime_postgres_dsn)
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
                "GOAT_WORKBENCH_LANGGRAPH_ENABLED",
                "GOAT_WORKBENCH_BROWSE_MAX_STEPS",
                "GOAT_WORKBENCH_DEEP_RESEARCH_MAX_STEPS",
            )
            try:
                _clear_env(*original_env.keys())
                os.environ["GOAT_WORKBENCH_WEB_PROVIDER"] = "duckduckgo"
                os.environ["GOAT_WORKBENCH_WEB_MAX_RESULTS"] = "7"
                os.environ["GOAT_WORKBENCH_WEB_TIMEOUT_SEC"] = "11"
                os.environ["GOAT_WORKBENCH_WEB_REGION"] = "us-en"
                os.environ["GOAT_WORKBENCH_WEB_SAFESEARCH"] = "off"
                os.environ["GOAT_WORKBENCH_LANGGRAPH_ENABLED"] = "false"
                os.environ["GOAT_WORKBENCH_BROWSE_MAX_STEPS"] = "1"
                os.environ["GOAT_WORKBENCH_DEEP_RESEARCH_MAX_STEPS"] = "4"
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
                self.assertFalse(settings.workbench_langgraph_enabled)
                self.assertEqual(1, settings.workbench_browse_max_steps)
                self.assertEqual(4, settings.workbench_deep_research_max_steps)
            finally:
                _restore_many(original_env)

    def test_load_settings_rejects_invalid_workbench_step_limits(self) -> None:
        original_env = _capture_env(
            "GOAT_WORKBENCH_BROWSE_MAX_STEPS",
            "GOAT_WORKBENCH_DEEP_RESEARCH_MAX_STEPS",
        )
        try:
            _clear_env(*original_env.keys())
            os.environ["GOAT_WORKBENCH_BROWSE_MAX_STEPS"] = "0"
            with self.assertRaisesRegex(ValueError, "GOAT_WORKBENCH_BROWSE_MAX_STEPS"):
                config.load_settings()
        finally:
            _restore_many(original_env)

    def test_load_settings_parses_workbench_connector_bindings_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app_root = Path(tmp)
            runtime_root = app_root / "var"
            original_env = _capture_env("GOAT_WORKBENCH_CONNECTOR_BINDINGS_JSON")
            try:
                _clear_env(*original_env.keys())
                os.environ["GOAT_WORKBENCH_CONNECTOR_BINDINGS_JSON"] = """
                [
                  {
                    "source_id": "connector:ops-runbook",
                    "display_name": "Ops Runbook",
                    "documents": [
                      {
                        "document_id": "connector://ops/runbook",
                        "title": "Ops Runbook",
                        "content": "Escalation runbook"
                      }
                    ],
                    "tenant_ids": ["tenant:default"]
                  }
                ]
                """
                with (
                    patch.object(config, "APP_ROOT", app_root),
                    patch.object(config, "DEFAULT_RUNTIME_ROOT", runtime_root),
                ):
                    settings = config.load_settings()
                self.assertIn(
                    "connector:ops-runbook",
                    settings.workbench_connector_bindings_json,
                )
            finally:
                _restore_many(original_env)

    def test_load_settings_rejects_invalid_workbench_connector_bindings(self) -> None:
        original_env = _capture_env("GOAT_WORKBENCH_CONNECTOR_BINDINGS_JSON")
        try:
            _clear_env(*original_env.keys())
            os.environ["GOAT_WORKBENCH_CONNECTOR_BINDINGS_JSON"] = """
            [
              {
                "source_id": "connector:ops-runbook",
                "display_name": "Ops Runbook",
                "documents": []
              }
            ]
            """
            with self.assertRaisesRegex(
                ValueError,
                "GOAT_WORKBENCH_CONNECTOR_BINDINGS_JSON documents must not be empty",
            ):
                config.load_settings()
        finally:
            _restore_many(original_env)

    def test_load_settings_uses_school_ollama_profile_only_when_opted_in(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app_root = Path(tmp)
            runtime_root = app_root / "var"
            dotenv_path = app_root / ".env"
            dotenv_path.write_text(
                "GOAT_USE_SCHOOL_OLLAMA_LOCAL=1\n",
                encoding="utf-8",
            )

            original_env = _capture_env(
                "GOAT_USE_SCHOOL_OLLAMA_LOCAL",
                "GOAT_OLLAMA_PROFILE",
                "OLLAMA_BASE_URL",
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
                self.assertEqual("http://127.0.0.1:11435", settings.ollama_base_url)
            finally:
                _restore_many(original_env)

    def test_load_settings_parses_shared_access_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app_root = Path(tmp)
            runtime_root = app_root / "var"
            original_env = _capture_env(
                "GOAT_SHARED_ACCESS_PASSWORD_HASH",
                "GOAT_SHARED_ACCESS_SESSION_SECRET",
                "GOAT_SHARED_ACCESS_SESSION_TTL_SEC",
            )
            try:
                _clear_env(*original_env.keys())
                os.environ["GOAT_SHARED_ACCESS_PASSWORD_HASH"] = (
                    hash_shared_access_password("goat-shared")
                )
                os.environ["GOAT_SHARED_ACCESS_SESSION_SECRET"] = "session-secret"
                os.environ["GOAT_SHARED_ACCESS_SESSION_TTL_SEC"] = "86400"
                with (
                    patch.object(config, "APP_ROOT", app_root),
                    patch.object(config, "DEFAULT_RUNTIME_ROOT", runtime_root),
                ):
                    settings = config.load_settings()
                self.assertEqual("", settings.shared_access_password)
                self.assertTrue(settings.shared_access_password_hash)
                self.assertEqual(
                    "session-secret", settings.shared_access_session_secret
                )
                self.assertEqual(86400, settings.shared_access_session_ttl_sec)
                self.assertTrue(settings.shared_access_enabled)
            finally:
                _restore_many(original_env)

    def test_load_settings_accepts_legacy_plaintext_shared_access_password(
        self,
    ) -> None:
        original_env = _capture_env(
            "GOAT_SHARED_ACCESS_PASSWORD",
            "GOAT_SHARED_ACCESS_PASSWORD_HASH",
            "GOAT_SHARED_ACCESS_SESSION_SECRET",
        )
        try:
            _clear_env(*original_env.keys())
            os.environ["GOAT_SHARED_ACCESS_PASSWORD"] = "goat-shared"
            os.environ["GOAT_SHARED_ACCESS_SESSION_SECRET"] = "session-secret"

            settings = config.load_settings()

            self.assertEqual("goat-shared", settings.shared_access_password)
            self.assertEqual("", settings.shared_access_password_hash)
            self.assertTrue(settings.shared_access_enabled)
        finally:
            _restore_many(original_env)

    def test_load_settings_rejects_shared_access_password_without_session_secret(
        self,
    ) -> None:
        original_env = _capture_env(
            "GOAT_SHARED_ACCESS_PASSWORD",
            "GOAT_SHARED_ACCESS_PASSWORD_HASH",
            "GOAT_SHARED_ACCESS_SESSION_SECRET",
        )
        try:
            _clear_env(*original_env.keys())
            os.environ["GOAT_SHARED_ACCESS_PASSWORD"] = "goat-shared"
            with self.assertRaisesRegex(
                ValueError, "GOAT_SHARED_ACCESS_SESSION_SECRET"
            ):
                config.load_settings()
        finally:
            _restore_many(original_env)

    def test_load_settings_rejects_non_positive_shared_access_ttl(self) -> None:
        original_env = _capture_env(
            "GOAT_SHARED_ACCESS_PASSWORD",
            "GOAT_SHARED_ACCESS_PASSWORD_HASH",
            "GOAT_SHARED_ACCESS_SESSION_SECRET",
            "GOAT_SHARED_ACCESS_SESSION_TTL_SEC",
        )
        try:
            _clear_env(*original_env.keys())
            os.environ["GOAT_SHARED_ACCESS_PASSWORD"] = "goat-shared"
            os.environ["GOAT_SHARED_ACCESS_SESSION_SECRET"] = "session-secret"
            os.environ["GOAT_SHARED_ACCESS_SESSION_TTL_SEC"] = "0"
            with self.assertRaisesRegex(
                ValueError, "GOAT_SHARED_ACCESS_SESSION_TTL_SEC"
            ):
                config.load_settings()
        finally:
            _restore_many(original_env)

    def test_load_settings_rejects_invalid_shared_access_password_hash(self) -> None:
        original_env = _capture_env(
            "GOAT_SHARED_ACCESS_PASSWORD_HASH",
            "GOAT_SHARED_ACCESS_SESSION_SECRET",
        )
        try:
            _clear_env(*original_env.keys())
            os.environ["GOAT_SHARED_ACCESS_PASSWORD_HASH"] = "definitely-not-a-hash"
            os.environ["GOAT_SHARED_ACCESS_SESSION_SECRET"] = "session-secret"
            with self.assertRaisesRegex(ValueError, "GOAT_SHARED_ACCESS_PASSWORD_HASH"):
                config.load_settings()
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
