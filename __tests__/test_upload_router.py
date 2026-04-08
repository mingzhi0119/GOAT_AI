from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
except ImportError:  # pragma: no cover - environment without backend deps
    FastAPI = None  # type: ignore[assignment]
    TestClient = None  # type: ignore[assignment]

from backend.models.upload import UploadAnalysisResponse
from backend.services import log_service
from goat_ai.config import Settings

if FastAPI is not None:
    from backend.config import get_settings
    from backend.exception_handlers import register_exception_handlers
    from backend.dependencies import get_llm_client
    from backend.routers import upload


class FakeUploadLLM:
    def generate_completion(
        self,
        model: str,
        prompt: str,
        *,
        ollama_options: dict[str, float | int] | None = None,
    ) -> str:
        return "Analyze this spreadsheet and tell me the main trends, outliers, and comparisons worth noting."


@unittest.skipUnless(
    FastAPI is not None and TestClient is not None, "fastapi not installed"
)
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
        register_exception_handlers(app)
        app.include_router(upload.router, prefix="/api")
        app.dependency_overrides[get_settings] = lambda: self.settings
        app.dependency_overrides[get_llm_client] = lambda: FakeUploadLLM()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_upload_analyze_returns_knowledge_rag_metadata_without_chart(self) -> None:
        response = self.client.post(
            "/api/upload/analyze",
            files={
                "file": ("data.csv", b"month,revenue\nJan,10\nFeb,12\n", "text/csv")
            },
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("data.csv", payload["filename"])
        self.assertIn("document_id", payload)
        self.assertIn("ingestion_id", payload)
        self.assertEqual("knowledge_rag", payload["retrieval_mode"])
        self.assertIn("suffix_prompt", payload)
        self.assertIn("template_prompt", payload)
        self.assertIsNone(payload["chart"])

    def test_upload_analyze_rejects_invalid_extension(self) -> None:
        response = self.client.post(
            "/api/upload/analyze",
            files={"file": ("data.bin", b"hello", "application/octet-stream")},
        )

        self.assertEqual(400, response.status_code)
        body = response.json()
        self.assertIn("Supported knowledge upload types", body["detail"])
        self.assertEqual("BAD_REQUEST", body["code"])

    def test_upload_analyze_idempotency_replays_same_body(self) -> None:
        headers = {"Idempotency-Key": "upload-key-1"}
        canned = UploadAnalysisResponse(
            filename="data.csv",
            suffix_prompt="Inspect this CSV for trends, anomalies, and key comparisons.",
            document_id="doc-cached",
            ingestion_id="ing-cached",
            status="completed",
            retrieval_mode="knowledge_rag",
            template_prompt="Analyze this CSV and tell me the main trends, outliers, and comparisons worth noting.",
            chart=None,
        )
        with patch(
            "backend.routers.upload.ingest_upload",
            return_value=canned,
        ) as ingest_mock:
            first = self.client.post(
                "/api/upload/analyze",
                files={"file": ("data.csv", b"month,revenue\nJan,10\n", "text/csv")},
                headers=headers,
            )
            second = self.client.post(
                "/api/upload/analyze",
                files={"file": ("data.csv", b"month,revenue\nJan,10\n", "text/csv")},
                headers=headers,
            )

        self.assertEqual(200, first.status_code)
        self.assertEqual(200, second.status_code)
        self.assertEqual(first.json(), second.json())
        self.assertEqual(1, ingest_mock.call_count)

    def test_upload_analyze_idempotency_rejects_payload_mismatch(self) -> None:
        headers = {"Idempotency-Key": "upload-key-mismatch"}
        first = self.client.post(
            "/api/upload/analyze",
            files={"file": ("data.csv", b"month,revenue\nJan,10\n", "text/csv")},
            headers=headers,
        )
        second = self.client.post(
            "/api/upload/analyze",
            files={"file": ("data.csv", b"month,revenue\nJan,11\n", "text/csv")},
            headers=headers,
        )
        self.assertEqual(200, first.status_code)
        self.assertEqual(409, second.status_code)
        body = second.json()
        self.assertEqual("IDEMPOTENCY_CONFLICT", body["code"])


if __name__ == "__main__":
    unittest.main()
