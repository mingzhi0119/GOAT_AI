from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
except ImportError:  # pragma: no cover - environment without backend deps
    FastAPI = None  # type: ignore[assignment]
    TestClient = None  # type: ignore[assignment]

from goat_ai.config import Settings

if FastAPI is not None:
    from backend.config import get_settings
    from backend.routers import system


@unittest.skipUnless(FastAPI is not None and TestClient is not None, "fastapi not installed")
class SystemRouterIntegrationTests(unittest.TestCase):
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
            deploy_target="auto",
            server_port=62606,
            local_port=8002,
        )

        app = FastAPI()
        app.include_router(system.router, prefix="/api")
        app.dependency_overrides[get_settings] = lambda: self.settings
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_get_runtime_target_returns_current_and_ordered_targets(self) -> None:
        response = self.client.get("/api/system/runtime-target")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("auto", payload["deploy_target"])
        self.assertIn("current", payload)
        self.assertIn("ordered_targets", payload)
        self.assertGreaterEqual(len(payload["ordered_targets"]), 1)
        self.assertIn(payload["current"]["mode"], {"server62606", "local", "explicit_override"})


if __name__ == "__main__":
    unittest.main()
