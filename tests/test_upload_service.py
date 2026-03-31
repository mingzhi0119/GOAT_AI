from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from backend.services import log_service
from backend.services.upload_service import stream_upload_analysis_sse
from goat_ai.config import Settings


class _FakeLLMClient:
    def stream_tokens(self, model, messages, system_prompt, *, ollama_options=None):
        yield "token-A"
        yield "token-B"


class UploadServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        app_root = Path(self.tmpdir.name)
        self.settings = Settings(
            ollama_base_url="http://127.0.0.1:11434",
            generate_timeout=120,
            max_upload_mb=20,
            max_upload_bytes=20 * 1024 * 1024,
            max_dataframe_rows=50000,
            use_chat_api=True,
            system_prompt="test",
            app_root=app_root,
            logo_svg=app_root / "logo.svg",
            log_db_path=app_root / "chat_logs.db",
        )
        log_service.init_db(self.settings.log_db_path)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_upload_stream_emits_file_context_event(self) -> None:
        content = b"col1,col2\n1,2\n"
        events = list(
            stream_upload_analysis_sse(
                llm=_FakeLLMClient(),
                model="llama3:latest",
                content=content,
                filename="data.csv",
                settings=self.settings,
            )
        )
        self.assertGreaterEqual(len(events), 2)

        first = events[0]
        self.assertTrue(first.startswith("data: "))
        payload = json.loads(first[len("data: ") :].strip())
        self.assertEqual("file_context", payload["type"])
        self.assertEqual("data.csv", payload["filename"])
        self.assertIn("col1", payload["prompt"])
        chart_payload = json.loads(events[1][len("data: ") :].strip())
        self.assertEqual("chart_spec", chart_payload["type"])
        self.assertIn("chart", chart_payload)
        self.assertEqual("line", chart_payload["chart"]["type"])
        self.assertTrue(any('"[DONE]"' in event for event in events))


if __name__ == "__main__":
    unittest.main()
