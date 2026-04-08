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
    from backend.exception_handlers import register_exception_handlers
    from backend.routers import code_sandbox, system


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
            local_port=62606,
        )

        app = FastAPI()
        register_exception_handlers(app)
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
        self.assertIn(payload["current"]["mode"], {"server62606", "explicit_override"})

    def test_get_system_features_includes_code_sandbox_snapshot(self) -> None:
        response = self.client.get("/api/system/features")
        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertIn("code_sandbox", body)
        cs = body["code_sandbox"]
        self.assertIn("allowed_by_config", cs)
        self.assertIn("available_on_host", cs)
        self.assertIn("effective_enabled", cs)
        self.assertIn("deny_reason", cs)
        self.assertIn("policy_allowed", cs)
        self.assertIsNone(cs["policy_allowed"])
        self.assertFalse(cs["allowed_by_config"])

    def test_code_sandbox_exec_forbidden_when_feature_off(self) -> None:
        app = FastAPI()
        register_exception_handlers(app)
        app.include_router(code_sandbox.router, prefix="/api")
        app.dependency_overrides[get_settings] = lambda: self.settings
        client = TestClient(app)
        r = client.post("/api/code-sandbox/exec")
        self.assertEqual(503, r.status_code)
        self.assertEqual("FEATURE_UNAVAILABLE", r.json()["code"])


if __name__ == "__main__":
    unittest.main()
