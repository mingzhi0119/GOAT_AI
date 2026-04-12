from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from backend.services.workbench_web_search import (
    WorkbenchWebSearchError,
    search_public_web,
)
from goat_ai.config.settings import Settings


def _settings(root: Path) -> Settings:
    return Settings(
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
    )


class _FakeDDGS:
    def __init__(self, *, timeout: int) -> None:
        self.timeout = timeout

    def text(
        self,
        query: str,
        *,
        region: str,
        safesearch: str,
        max_results: int,
    ) -> list[dict[str, object]]:
        _ = (query, region, safesearch, max_results)
        return [
            {
                "title": "Example result",
                "href": "https://example.com/report",
                "body": "First result",
            },
            {
                "title": "",
                "href": "https://example.com/report",
                "body": "Duplicate URL should be removed",
            },
            {
                "title": "",
                "href": "https://docs.example.com/article",
                "body": "Second result",
            },
            {
                "title": "Missing snippet",
                "href": "https://example.com/empty",
                "body": "",
            },
        ]


class WorkbenchWebSearchTests(unittest.TestCase):
    def test_search_public_web_uses_ddgs_and_normalizes_hits(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            settings = replace(
                _settings(Path(tmp)),
                workbench_web_max_results=2,
                workbench_web_region="us-en",
                workbench_web_safesearch="off",
                workbench_web_timeout_sec=9,
            )

            with patch(
                "backend.services.workbench_web_search.DDGS",
                side_effect=lambda **kwargs: _FakeDDGS(timeout=kwargs["timeout"]),
            ):
                hits = search_public_web(
                    query="recent launch",
                    settings=settings,
                    max_results=5,
                )

        self.assertEqual(2, len(hits))
        self.assertEqual("Example result", hits[0].title)
        self.assertEqual("https://example.com/report", hits[0].url)
        self.assertEqual("docs.example.com", hits[1].title)
        self.assertEqual("Second result", hits[1].snippet)

    def test_search_public_web_rejects_disabled_provider(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            settings = replace(
                _settings(Path(tmp)),
                workbench_web_provider="disabled",
            )
            with self.assertRaisesRegex(WorkbenchWebSearchError, "disabled"):
                search_public_web(
                    query="recent launch",
                    settings=settings,
                    max_results=3,
                )


if __name__ == "__main__":
    unittest.main()
