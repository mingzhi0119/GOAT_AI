from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend import main
from backend.platform.otel_middleware import OtelTraceContextMiddleware
from goat_ai.config.settings import Settings


class BackendMainFactoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        root = Path(self.tmpdir.name)
        self.settings = Settings(
            ollama_base_url="http://127.0.0.1:11434",
            generate_timeout=120,
            max_upload_mb=20,
            max_upload_bytes=20 * 1024 * 1024,
            max_dataframe_rows=50000,
            use_chat_api=True,
            system_prompt="test",
            app_root=root,
            logo_svg=root / "logo.svg",
            log_db_path=root / "chat_logs.db",
            deploy_mode=0,
            server_port=62606,
            local_port=62606,
        )

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_create_contract_app_skips_runtime_initializers(self) -> None:
        with (
            patch.object(
                main, "initialize_runtime_metadata_store"
            ) as initialize_runtime_metadata_store,
            patch.object(main, "init_latency_metrics") as init_latency_metrics,
            patch.object(main, "init_otel_if_enabled") as init_otel_if_enabled,
        ):
            app = main.create_contract_app(self.settings)

        initialize_runtime_metadata_store.assert_not_called()
        init_latency_metrics.assert_not_called()
        init_otel_if_enabled.assert_not_called()
        self.assertIn("/api/health", app.openapi()["paths"])

    def test_create_app_runs_runtime_initializers(self) -> None:
        with (
            patch.object(main, "get_settings", return_value=self.settings),
            patch.object(main, "configure_logging") as configure_logging,
            patch.object(
                main, "initialize_runtime_metadata_store"
            ) as initialize_runtime_metadata_store,
            patch.object(main, "init_latency_metrics") as init_latency_metrics,
            patch.object(main, "init_otel_if_enabled") as init_otel_if_enabled,
            patch.object(main, "is_otel_enabled", return_value=False),
        ):
            app = main.create_app()

        configure_logging.assert_called_once_with()
        initialize_runtime_metadata_store.assert_called_once_with(self.settings)
        init_latency_metrics.assert_called_once_with(
            self.settings.latency_rolling_max_samples
        )
        init_otel_if_enabled.assert_called_once_with()
        self.assertIn("/api/health", app.openapi()["paths"])

    def test_create_app_adds_otel_middleware_when_enabled(self) -> None:
        with (
            patch.dict(
                os.environ,
                {"GOAT_OTEL_ENABLED": "1", "GOAT_OTEL_EXPORTER": "console"},
                clear=True,
            ),
            patch.object(main, "get_settings", return_value=self.settings),
            patch.object(main, "configure_logging") as configure_logging,
            patch.object(
                main, "initialize_runtime_metadata_store"
            ) as initialize_runtime_metadata_store,
            patch.object(main, "init_latency_metrics") as init_latency_metrics,
            patch.object(main, "init_otel_if_enabled") as init_otel_if_enabled,
        ):
            app = main.create_app()

        configure_logging.assert_called_once_with()
        initialize_runtime_metadata_store.assert_called_once_with(self.settings)
        init_latency_metrics.assert_called_once_with(
            self.settings.latency_rolling_max_samples
        )
        init_otel_if_enabled.assert_called_once_with()
        self.assertIn(
            OtelTraceContextMiddleware,
            [entry.cls for entry in app.user_middleware],
        )

    def test_create_app_accepts_postgres_runtime_metadata_backend(
        self,
    ) -> None:
        postgres_settings = Settings(
            **(
                self.settings.__dict__
                | {
                    "runtime_metadata_backend": "postgres",
                    "runtime_postgres_dsn": (
                        "postgresql://goat:secret@db.example.com:5432/goat"
                    ),
                    "deploy_mode": 2,
                }
            )
        )

        with (
            patch.object(main, "get_settings", return_value=postgres_settings),
            patch.object(main, "configure_logging") as configure_logging,
            patch.object(
                main, "initialize_runtime_metadata_store"
            ) as initialize_runtime_metadata_store,
            patch.object(main, "init_latency_metrics") as init_latency_metrics,
            patch.object(main, "init_otel_if_enabled") as init_otel_if_enabled,
            patch.object(main, "is_otel_enabled", return_value=False),
        ):
            app = main.create_app()

        configure_logging.assert_called_once_with()
        initialize_runtime_metadata_store.assert_called_once_with(postgres_settings)
        init_latency_metrics.assert_called_once_with(
            postgres_settings.latency_rolling_max_samples
        )
        init_otel_if_enabled.assert_called_once_with()
        self.assertIn("/api/health", app.openapi()["paths"])
