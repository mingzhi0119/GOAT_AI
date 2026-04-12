from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from backend.platform.readiness_service import evaluate_readiness
from goat_ai.config.settings import Settings


def _settings(*, ready_skip_ollama_probe: bool = False) -> Settings:
    root = Path(tempfile.gettempdir()) / "goat-ai-readiness-tests"
    root.mkdir(parents=True, exist_ok=True)
    return Settings(
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
        ready_skip_ollama_probe=ready_skip_ollama_probe,
    )


class ReadinessServiceTests(unittest.TestCase):
    def test_readiness_skips_ollama_probe_when_configured(self) -> None:
        body, status = evaluate_readiness(_settings(ready_skip_ollama_probe=True))

        self.assertEqual(200, status)
        self.assertTrue(body["ready"])
        self.assertTrue(body["checks"]["sqlite"]["ok"])
        self.assertTrue(body["checks"]["ollama"]["skipped"])

    def test_readiness_reports_sqlite_failure(self) -> None:
        with patch(
            "backend.platform.readiness_service.sqlite3.connect",
            side_effect=OSError("db locked"),
        ):
            body, status = evaluate_readiness(_settings(ready_skip_ollama_probe=True))

        self.assertEqual(503, status)
        self.assertFalse(body["ready"])
        self.assertFalse(body["checks"]["sqlite"]["ok"])
        self.assertIn("db locked", body["checks"]["sqlite"]["error"])

    def test_readiness_reports_ollama_failure(self) -> None:
        with patch(
            "backend.platform.readiness_service.requests.get",
            side_effect=RuntimeError("connection refused"),
        ):
            body, status = evaluate_readiness(_settings())

        self.assertEqual(503, status)
        self.assertFalse(body["ready"])
        self.assertFalse(body["checks"]["ollama"]["ok"])
        self.assertIn("/api/tags", body["checks"]["ollama"]["url"])

    def test_readiness_reports_ollama_success(self) -> None:
        response = Mock()
        response.status_code = 200
        response.raise_for_status.return_value = None
        with patch(
            "backend.platform.readiness_service.requests.get", return_value=response
        ):
            body, status = evaluate_readiness(_settings())

        self.assertEqual(200, status)
        self.assertTrue(body["ready"])
        self.assertEqual(200, body["checks"]["ollama"]["http_status"])


if __name__ == "__main__":
    unittest.main()
