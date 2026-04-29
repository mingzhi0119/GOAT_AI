from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import requests
from ddgs.exceptions import DDGSException

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
        serper_api_key="serper-test-key",
    )


class _FakeSerperResponse:
    def __init__(
        self,
        *,
        payload: object,
        status_code: int = 200,
        malformed_json: bool = False,
    ) -> None:
        self._payload = payload
        self.status_code = status_code
        self._malformed_json = malformed_json

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            error = requests.HTTPError("http failure")
            error.response = self  # type: ignore[assignment]
            raise error

    def json(self) -> object:
        if self._malformed_json:
            raise ValueError("bad json")
        return self._payload


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
                "href": "https://docs.example.com/article",
                "body": "Second result",
            },
        ]


class WorkbenchWebSearchTests(unittest.TestCase):
    def test_search_public_web_uses_serper_and_normalizes_hits(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            settings = replace(
                _settings(Path(tmp)),
                workbench_web_max_results=2,
                workbench_web_timeout_sec=9,
                serper_gl="ca",
                serper_hl="fr",
            )
            calls: list[dict[str, object]] = []

            def _fake_post(*args: object, **kwargs: object) -> _FakeSerperResponse:
                calls.append({"args": args, **kwargs})
                return _FakeSerperResponse(
                    payload={
                        "organic": [
                            {
                                "title": "Example result",
                                "link": "https://example.com/report",
                                "snippet": "First result",
                                "position": 4,
                            },
                            {
                                "title": "Duplicate",
                                "link": "https://example.com/report",
                                "snippet": "Duplicate URL should be removed",
                                "position": 5,
                            },
                            {
                                "title": "",
                                "link": "https://docs.example.com/article",
                                "snippet": "Second result",
                            },
                            {
                                "title": "Missing snippet",
                                "link": "https://example.com/empty",
                                "snippet": "",
                            },
                        ]
                    }
                )

            with patch(
                "goat_ai.search.providers.requests.post", side_effect=_fake_post
            ):
                hits = search_public_web(
                    query="recent launch",
                    settings=settings,
                    max_results=5,
                )

        self.assertEqual(2, len(hits))
        self.assertEqual("Example result", hits[0].title)
        self.assertEqual("https://example.com/report", hits[0].url)
        self.assertEqual(4, hits[0].rank)
        self.assertEqual("serper", hits[0].provider)
        self.assertEqual("docs.example.com", hits[1].title)
        self.assertEqual("Second result", hits[1].snippet)
        self.assertEqual("https://google.serper.dev/search", calls[0]["args"][0])
        self.assertEqual(
            {
                "X-API-KEY": "serper-test-key",
                "Content-Type": "application/json",
            },
            calls[0]["headers"],
        )
        self.assertEqual(
            {"q": "recent launch", "num": 2, "gl": "ca", "hl": "fr"},
            calls[0]["json"],
        )
        self.assertEqual(9, calls[0]["timeout"])

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

    def test_search_public_web_falls_back_to_duckduckgo_without_serper_key(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            settings = replace(_settings(Path(tmp)), serper_api_key="")
            with (
                patch("goat_ai.search.providers.requests.post") as post,
                patch(
                    "goat_ai.search.providers.DDGS",
                    side_effect=lambda **kwargs: _FakeDDGS(timeout=kwargs["timeout"]),
                ),
            ):
                hits = search_public_web(
                    query="recent launch",
                    settings=settings,
                    max_results=3,
                )

        post.assert_not_called()
        self.assertEqual(2, len(hits))
        self.assertEqual("duckduckgo", hits[0].provider)

    def test_search_public_web_falls_back_to_duckduckgo_on_serper_failures(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            settings = _settings(Path(tmp))
            cases = [
                requests.Timeout("timeout"),
                _FakeSerperResponse(payload={}, status_code=429),
                _FakeSerperResponse(payload={}, status_code=500),
                _FakeSerperResponse(payload={}, malformed_json=True),
                _FakeSerperResponse(payload=[]),
                _FakeSerperResponse(payload={"organic": "bad"}),
            ]
            for case in cases:
                with self.subTest(case=case):
                    with (
                        patch(
                            "goat_ai.search.providers.requests.post",
                            side_effect=(
                                case if isinstance(case, BaseException) else None
                            ),
                            return_value=(
                                None if isinstance(case, BaseException) else case
                            ),
                        ),
                        patch(
                            "goat_ai.search.providers.DDGS",
                            side_effect=lambda **kwargs: _FakeDDGS(
                                timeout=kwargs["timeout"]
                            ),
                        ),
                    ):
                        hits = search_public_web(
                            query="recent launch",
                            settings=settings,
                            max_results=3,
                        )
                    self.assertEqual(2, len(hits))
                    self.assertEqual("duckduckgo", hits[0].provider)

    def test_search_public_web_reports_unavailable_when_serper_and_fallback_fail(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            settings = replace(_settings(Path(tmp)), serper_api_key="")
            with patch(
                "goat_ai.search.providers.DDGS",
                side_effect=DDGSException("ddg unavailable"),
            ):
                with self.assertRaisesRegex(
                    WorkbenchWebSearchError,
                    "Serper search unavailable.*DuckDuckGo fallback failed",
                ):
                    search_public_web(
                        query="recent launch",
                        settings=settings,
                        max_results=3,
                    )

    def test_search_public_web_returns_empty_serper_results(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            settings = _settings(Path(tmp))
            with patch(
                "goat_ai.search.providers.requests.post",
                return_value=_FakeSerperResponse(payload={"organic": []}),
            ):
                hits = search_public_web(
                    query="recent launch",
                    settings=settings,
                    max_results=3,
                )

        self.assertEqual([], hits)

    def test_search_public_web_allows_explicit_duckduckgo_provider(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            settings = replace(
                _settings(Path(tmp)),
                workbench_web_provider="duckduckgo",
                workbench_web_max_results=2,
                workbench_web_region="us-en",
                workbench_web_safesearch="off",
                workbench_web_timeout_sec=9,
            )

            with patch(
                "goat_ai.search.providers.DDGS",
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
        self.assertEqual("duckduckgo", hits[0].provider)
        self.assertEqual("docs.example.com", hits[1].title)


if __name__ == "__main__":
    unittest.main()
