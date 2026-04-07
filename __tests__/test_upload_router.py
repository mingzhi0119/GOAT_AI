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

from backend.services import log_service
from goat_ai.config import Settings

if FastAPI is not None:
    from backend.config import get_settings
    from backend.routers import upload


@unittest.skipUnless(FastAPI is not None and TestClient is not None, "fastapi not installed")
class UploadRouterIntegrationTests(unittest.TestCase):
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
        )
        log_service.init_db(self.settings.log_db_path)

        app = FastAPI()
        app.include_router(upload.router, prefix="/api")
        app.dependency_overrides[get_settings] = lambda: self.settings
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_upload_analyze_returns_prompt_and_chart(self) -> None:
        response = self.client.post(
            "/api/upload/analyze",
            files={"file": ("data.csv", b"month,revenue\nJan,10\nFeb,12\n", "text/csv")},
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("data.csv", payload["filename"])
        self.assertIn("month", payload["prompt"])
        self.assertIsNotNone(payload["chart"])
        self.assertEqual("line", payload["chart"]["type"])

    def test_upload_analyze_rejects_invalid_extension(self) -> None:
        response = self.client.post(
            "/api/upload/analyze",
            files={"file": ("notes.txt", b"hello", "text/plain")},
        )

        self.assertEqual(400, response.status_code)
        self.assertEqual("Only CSV and XLSX files are supported.", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
