"""Black-box tests for Phase 15.5 AuthZ: scoped API keys and session ownership."""

from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

try:
    from fastapi.testclient import TestClient
except ImportError:  # pragma: no cover
    TestClient = None  # type: ignore[assignment]

from backend.api_errors import AUTH_SESSION_OWNER_REQUIRED, AUTH_WRITE_KEY_REQUIRED
from goat_ai.config import Settings

if TestClient is not None:
    from backend.config import get_settings
    from backend.dependencies import get_llm_client, get_title_generator
    from backend.main import create_app
    from backend.models.chat import ChatMessage
    from backend.services import log_service
    from backend.services.session_message_codec import (
        SESSION_PAYLOAD_VERSION,
        build_session_payload,
    )
    from test_api_blackbox_contract import ContractFakeLLM, FakeTitleGenerator


@unittest.skipUnless(TestClient is not None, "fastapi not installed")
class ApiAuthzTests(unittest.TestCase):
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
            system_prompt="test system prompt",
            app_root=root,
            logo_svg=root / "logo.svg",
            log_db_path=root / "chat_logs.db",
            data_dir=root / "data",
            api_key="read-key",
            api_key_write="write-key",
            rate_limit_window_sec=60,
            rate_limit_max_requests=1000,
            ready_skip_ollama_probe=True,
        )
        log_service.init_db(self.settings.log_db_path)

        app = create_app()
        app.dependency_overrides[get_settings] = lambda: self.settings
        app.dependency_overrides[get_llm_client] = lambda: ContractFakeLLM()
        app.dependency_overrides[get_title_generator] = lambda: FakeTitleGenerator()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_read_key_forbidden_on_post_chat(self) -> None:
        headers = {"X-GOAT-API-Key": "read-key"}
        response = self.client.post(
            "/api/chat",
            headers=headers,
            json={
                "model": "blackbox-model",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )
        self.assertEqual(403, response.status_code)
        body = response.json()
        self.assertEqual(AUTH_WRITE_KEY_REQUIRED, body["code"])

    def test_read_key_allows_get_history(self) -> None:
        headers = {"X-GOAT-API-Key": "read-key"}
        response = self.client.get("/api/history", headers=headers)
        self.assertEqual(200, response.status_code)
        self.assertEqual({"sessions": []}, response.json())

    def test_require_session_owner_chat_without_header_returns_403(self) -> None:
        self.settings = replace(self.settings, require_session_owner=True)
        self.client.app.dependency_overrides[get_settings] = lambda: self.settings
        headers = {"X-GOAT-API-Key": "write-key"}
        response = self.client.post(
            "/api/chat",
            headers=headers,
            json={
                "model": "blackbox-model",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )
        self.assertEqual(403, response.status_code)
        self.assertEqual(AUTH_SESSION_OWNER_REQUIRED, response.json()["code"])

    def test_owner_mismatch_returns_404_on_history_get(self) -> None:
        ts = datetime(2026, 4, 8, 12, 0, 0, tzinfo=timezone.utc).isoformat()
        payload = build_session_payload(
            messages=[ChatMessage(role="user", content="hi")],
            assistant_text="yo",
            chart_spec=None,
            knowledge_documents=None,
            chart_data_source="none",
        )
        log_service.upsert_session(
            db_path=self.settings.log_db_path,
            session_id="sess-authz-1",
            title="T",
            model="m",
            schema_version=SESSION_PAYLOAD_VERSION,
            payload=payload,
            created_at=ts,
            updated_at=ts,
            owner_id="alice",
        )
        headers = {"X-GOAT-API-Key": "read-key", "X-GOAT-Owner-Id": "bob"}
        response = self.client.get("/api/history/sess-authz-1", headers=headers)
        self.assertEqual(404, response.status_code)


if __name__ == "__main__":
    unittest.main()
