from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

try:
    from fastapi.testclient import TestClient
except ImportError:  # pragma: no cover - environment without backend deps
    TestClient = None  # type: ignore[assignment]

from goat_ai.config import Settings

if TestClient is not None:
    from backend.config import get_settings
    from backend.main import create_app
    from backend.services import log_service


@unittest.skipUnless(TestClient is not None, "fastapi not installed")
class ApiSecurityIntegrationTests(unittest.TestCase):
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
            api_key="secret-123",
            rate_limit_window_sec=60,
            rate_limit_max_requests=2,
        )
        log_service.init_db(self.settings.log_db_path)

        app = create_app()
        app.dependency_overrides[get_settings] = lambda: self.settings
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_health_endpoint_remains_unprotected(self) -> None:
        resp = self.client.get("/api/health")
        self.assertEqual(200, resp.status_code)
        self.assertEqual("ok", resp.json()["status"])
        self.assertIn("X-Request-ID", resp.headers)

    def test_non_health_endpoint_requires_api_key(self) -> None:
        missing = self.client.get("/api/history")
        self.assertEqual(401, missing.status_code)

        wrong = self.client.get("/api/history", headers={"X-GOAT-API-Key": "wrong"})
        self.assertEqual(401, wrong.status_code)

        ok = self.client.get("/api/history", headers={"X-GOAT-API-Key": "secret-123"})
        self.assertEqual(200, ok.status_code)
        self.assertEqual({"sessions": []}, ok.json())

    def test_rate_limit_applies_after_threshold(self) -> None:
        headers = {"X-GOAT-API-Key": "secret-123"}
        self.assertEqual(200, self.client.get("/api/history", headers=headers).status_code)
        self.assertEqual(200, self.client.get("/api/history", headers=headers).status_code)

        limited = self.client.get("/api/history", headers=headers)
        self.assertEqual(429, limited.status_code)
        self.assertEqual("Too many requests. Please try again shortly.", limited.json()["detail"])
        self.assertIn("Retry-After", limited.headers)


if __name__ == "__main__":
    unittest.main()
