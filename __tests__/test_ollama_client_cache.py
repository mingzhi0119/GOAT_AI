from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import requests

from goat_ai.config import Settings
from goat_ai.exceptions import OllamaUnavailable
from goat_ai.ollama_client import OllamaService, _iter_stream_parts_from_chunk


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


def test_iter_stream_parts_message_thinking_when_content_empty() -> None:
    chunk = {
        "model": "qwen3",
        "message": {"role": "assistant", "thinking": "step ", "content": ""},
        "done": False,
    }
    parts = _iter_stream_parts_from_chunk(chunk)
    assert [(p.kind, p.text) for p in parts] == [("thinking", "step ")]


def test_iter_stream_parts_thinking_then_content_in_one_chunk() -> None:
    chunk = {
        "message": {"role": "assistant", "thinking": "a", "content": "b"},
        "done": False,
    }
    parts = _iter_stream_parts_from_chunk(chunk)
    assert [(p.kind, p.text) for p in parts] == [("thinking", "a"), ("content", "b")]


def test_iter_stream_parts_generate_thinking_when_no_response() -> None:
    chunk = {"thinking": "trace", "done": False}
    parts = _iter_stream_parts_from_chunk(chunk)
    assert [(p.kind, p.text) for p in parts] == [("thinking", "trace")]


def test_stream_tokens_uses_chat_first_event_timeout() -> None:
    base = _settings(ttl=60)
    settings = Settings(
        **{
            **base.__dict__,
            "chat_first_event_timeout_sec": 77,
        }
    )
    service = OllamaService(settings)

    fake_response = Mock()
    fake_response.raise_for_status.return_value = None
    fake_response.iter_lines.return_value = []

    with patch(
        "goat_ai.ollama_client.requests.post", return_value=fake_response
    ) as post_mock:
        list(service.stream_tokens("gemma4:26b", [], "system"))

    assert post_mock.call_args is not None
    assert post_mock.call_args.kwargs["timeout"] == (5.0, 77.0)


def test_generate_completion_uses_generate_timeout() -> None:
    base = _settings(ttl=60)
    settings = Settings(
        **{
            **base.__dict__,
            "generate_timeout": 123,
        }
    )
    service = OllamaService(settings)

    fake_response = Mock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.return_value = {"response": "ok"}

    with patch(
        "goat_ai.ollama_client.requests.post", return_value=fake_response
    ) as post_mock:
        text = service.generate_completion("gemma4:26b", "hello")

    assert text == "ok"
    assert post_mock.call_args is not None
    assert post_mock.call_args.kwargs["timeout"] == 123.0


def test_get_model_capabilities_uses_ttl_cache() -> None:
    service = OllamaService(_settings(ttl=60))

    fake_response = Mock()
    fake_response.json.return_value = {"capabilities": ["completion", "tools"]}
    fake_response.raise_for_status.return_value = None

    with patch(
        "goat_ai.ollama_client.requests.post", return_value=fake_response
    ) as post_mock:
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

    with patch(
        "goat_ai.ollama_client.requests.post", return_value=fake_response
    ) as post_mock:
        service.get_model_capabilities("gemma4:26b")
        service.get_model_capabilities("gemma4:26b")

    assert post_mock.call_count == 2


def test_describe_model_for_api_parses_context_length() -> None:
    service = OllamaService(_settings(ttl=60))

    fake_response = Mock()
    fake_response.json.return_value = {
        "capabilities": ["completion"],
        "model_info": {"llama.context_length": 4096},
    }
    fake_response.raise_for_status.return_value = None

    with patch("goat_ai.ollama_client.requests.post", return_value=fake_response):
        caps, ctx = service.describe_model_for_api("ctx-parse-model")

    assert caps == ["completion"]
    assert ctx == 4096


def test_get_model_context_length_reuses_show_cache() -> None:
    service = OllamaService(_settings(ttl=60))

    fake_response = Mock()
    fake_response.json.return_value = {
        "capabilities": ["completion"],
        "model_info": {"llama.context_length": 8192},
    }
    fake_response.raise_for_status.return_value = None

    with patch(
        "goat_ai.ollama_client.requests.post", return_value=fake_response
    ) as post_mock:
        assert service.get_model_capabilities("m") == ["completion"]
        assert service.get_model_context_length("m") == 8192

    assert post_mock.call_count == 1


def test_list_model_names_retries_then_succeeds() -> None:
    service = OllamaService(_settings(ttl=60))
    failing = requests.ConnectionError("temporary outage")
    success = Mock()
    success.raise_for_status.return_value = None
    success.json.return_value = {"models": [{"name": "qwen3"}]}

    with (
        patch(
            "goat_ai.ollama_client.requests.get", side_effect=[failing, success]
        ) as get_mock,
        patch("goat_ai.ollama_client.time.sleep") as sleep_mock,
        patch("goat_ai.ollama_client.random.uniform", return_value=0.0),
    ):
        names = service.list_model_names()

    assert names == ["qwen3"]
    assert get_mock.call_count == 2
    assert sleep_mock.call_count == 1


def test_read_circuit_breaker_opens_and_half_open_recovers() -> None:
    base = _settings(ttl=0)
    tuned = Settings(
        **{
            **base.__dict__,
            "ollama_read_retry_attempts": 1,
            "ollama_circuit_breaker_failures": 1,
            "ollama_circuit_breaker_open_sec": 10,
        }
    )
    service = OllamaService(tuned)

    with patch(
        "goat_ai.ollama_client.requests.get",
        side_effect=requests.ConnectionError("down"),
    ) as get_mock:
        try:
            service.list_model_names()
            assert False, "Expected OllamaUnavailable"
        except OllamaUnavailable:
            pass
    assert get_mock.call_count == 1

    with patch("goat_ai.ollama_client.requests.get") as blocked_mock:
        try:
            service.list_model_names()
            assert False, "Expected open breaker rejection"
        except OllamaUnavailable:
            pass
    assert blocked_mock.call_count == 0

    success = Mock()
    success.raise_for_status.return_value = None
    success.json.return_value = {"models": [{"name": "gemma4:26b"}]}
    with (
        patch("goat_ai.ollama_client.time.monotonic", return_value=999.0),
        patch(
            "goat_ai.ollama_client.requests.get", return_value=success
        ) as recovered_get,
    ):
        service._breaker_open_until_monotonic = 100.0
        names = service.list_model_names()

    assert names == ["gemma4:26b"]
    assert recovered_get.call_count == 1
