from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

from goat_ai.config import Settings
from goat_ai.ollama_client import OllamaService


def _settings(*, ttl: int) -> Settings:
    return Settings(
        ollama_base_url="http://127.0.0.1:11434",
        generate_timeout=120,
        max_upload_mb=20,
        max_upload_bytes=20 * 1024 * 1024,
        max_dataframe_rows=50000,
        use_chat_api=True,
        system_prompt="test",
        app_root=Path("."),
        logo_svg=Path("logo.svg"),
        log_db_path=Path("chat_logs.db"),
        model_cap_cache_ttl_sec=ttl,
    )


def test_get_model_capabilities_uses_ttl_cache() -> None:
    service = OllamaService(_settings(ttl=60))

    fake_response = Mock()
    fake_response.json.return_value = {"capabilities": ["completion", "tools"]}
    fake_response.raise_for_status.return_value = None

    with patch("goat_ai.ollama_client.requests.post", return_value=fake_response) as post_mock:
        first = service.get_model_capabilities("qwen3")
        second = service.get_model_capabilities("qwen3")

    assert first == ["completion", "tools"]
    assert second == ["completion", "tools"]
    assert post_mock.call_count == 1


def test_get_model_capabilities_without_cache_calls_each_time() -> None:
    service = OllamaService(_settings(ttl=0))

    fake_response = Mock()
    fake_response.json.return_value = {"capabilities": ["completion"]}
    fake_response.raise_for_status.return_value = None

    with patch("goat_ai.ollama_client.requests.post", return_value=fake_response) as post_mock:
        service.get_model_capabilities("gemma4:26b")
        service.get_model_capabilities("gemma4:26b")

    assert post_mock.call_count == 2
