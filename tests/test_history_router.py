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
    from backend.routers import history


@unittest.skipUnless(FastAPI is not None and TestClient is not None, "fastapi not installed")
class HistoryRouterIntegrationTests(unittest.TestCase):
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
        app.include_router(history.router, prefix="/api")
        app.dependency_overrides[get_settings] = lambda: self.settings
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_list_get_delete_history_routes(self) -> None:
        session_id = "hist-1"
        log_service.upsert_session(
            db_path=self.settings.log_db_path,
            session_id=session_id,
            title="Case discussion",
            model="llama3:latest",
            messages=[
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "world"},
            ],
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:01+00:00",
        )

        list_resp = self.client.get("/api/history")
        self.assertEqual(200, list_resp.status_code)
        list_data = list_resp.json()
        self.assertIn("sessions", list_data)
        self.assertEqual(1, len(list_data["sessions"]))
        self.assertEqual(session_id, list_data["sessions"][0]["id"])

        detail_resp = self.client.get(f"/api/history/{session_id}")
        self.assertEqual(200, detail_resp.status_code)
        detail_data = detail_resp.json()
        self.assertEqual("Case discussion", detail_data["title"])
        self.assertEqual(2, len(detail_data["messages"]))

        missing_resp = self.client.get("/api/history/not-found")
        self.assertEqual(404, missing_resp.status_code)

        delete_resp = self.client.delete(f"/api/history/{session_id}")
        self.assertEqual(204, delete_resp.status_code)

        post_delete = self.client.get(f"/api/history/{session_id}")
        self.assertEqual(404, post_delete.status_code)


if __name__ == "__main__":
    unittest.main()
