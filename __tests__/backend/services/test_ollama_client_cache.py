from __future__ import annotations

import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from goat_ai.config.settings import Settings
from goat_ai.shared.exceptions import OllamaUnavailable
from goat_ai.llm.ollama_client import OllamaService, _iter_stream_parts_from_chunk


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
        ollama_max_concurrent_requests=2,
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
        "goat_ai.llm.ollama_client.requests.post", return_value=fake_response
    ) as post_mock:
        list(service.stream_tokens("qwen3:4b", [], "system"))

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
        "goat_ai.llm.ollama_client.requests.post", return_value=fake_response
    ) as post_mock:
        text = service.generate_completion("qwen3:4b", "hello")

    assert text == "ok"
    assert post_mock.call_args is not None
    assert post_mock.call_args.kwargs["timeout"] == 123.0


def test_stream_tokens_midstream_disconnect_raises_ollama_unavailable() -> None:
    service = OllamaService(_settings(ttl=60))

    class _BrokenResponse:
        def raise_for_status(self) -> None:
            return None

        def iter_lines(self):
            yield b'{"message":{"role":"assistant","content":"Hello"},"done":false}'
            raise requests.exceptions.ChunkedEncodingError("stream interrupted")

    with patch(
        "goat_ai.llm.ollama_client.requests.post", return_value=_BrokenResponse()
    ):
        with patch("goat_ai.llm.ollama_client.inc_ollama_error") as error_counter:
            try:
                list(service.stream_tokens("qwen3:4b", [], "system"))
                assert False, "Expected OllamaUnavailable"
            except OllamaUnavailable as exc:
                assert "interrupted" in str(exc)

    assert error_counter.call_count == 1


def test_get_model_capabilities_uses_ttl_cache() -> None:
    service = OllamaService(_settings(ttl=60))

    fake_response = Mock()
    fake_response.json.return_value = {"capabilities": ["completion", "tools"]}
    fake_response.raise_for_status.return_value = None

    with patch(
        "goat_ai.llm.ollama_client.requests.post", return_value=fake_response
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
        "goat_ai.llm.ollama_client.requests.post", return_value=fake_response
    ) as post_mock:
        service.get_model_capabilities("qwen3:4b")
        service.get_model_capabilities("qwen3:4b")

    assert post_mock.call_count == 2


def test_describe_model_for_api_parses_context_length() -> None:
    service = OllamaService(_settings(ttl=60))

    fake_response = Mock()
    fake_response.json.return_value = {
        "capabilities": ["completion"],
        "model_info": {"llama.context_length": 4096},
    }
    fake_response.raise_for_status.return_value = None

    with patch("goat_ai.llm.ollama_client.requests.post", return_value=fake_response):
        caps, ctx = service.describe_model_for_api("qwen3:4b")

    assert caps == ["completion"]
    assert ctx == 4096


def test_get_model_context_length_reuses_show_cache() -> None:
    service = OllamaService(_settings(ttl=60))
    service._cap_cache.clear()

    fake_response = Mock()
    fake_response.json.return_value = {
        "capabilities": ["completion"],
        "model_info": {"llama.context_length": 8192},
    }
    fake_response.raise_for_status.return_value = None

    with patch(
        "goat_ai.llm.ollama_client.requests.post", return_value=fake_response
    ) as post_mock:
        assert service.get_model_capabilities("qwen3:4b") == ["completion"]
        assert service.get_model_context_length("qwen3:4b") == 8192

    assert post_mock.call_count == 1


def test_list_model_names_retries_then_succeeds() -> None:
    service = OllamaService(_settings(ttl=60))
    failing = requests.ConnectionError("temporary outage")
    success = Mock()
    success.raise_for_status.return_value = None
    success.json.return_value = {"models": [{"name": "qwen3"}]}

    with (
        patch(
            "goat_ai.llm.ollama_client.requests.get", side_effect=[failing, success]
        ) as get_mock,
        patch("goat_ai.llm.ollama_client.time.sleep") as sleep_mock,
        patch("goat_ai.llm.ollama_client.random.uniform", return_value=0.0),
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
        "goat_ai.llm.ollama_client.requests.get",
        side_effect=requests.ConnectionError("down"),
    ) as get_mock:
        try:
            service.list_model_names()
            assert False, "Expected OllamaUnavailable"
        except OllamaUnavailable:
            pass
    assert get_mock.call_count == 1

    with patch("goat_ai.llm.ollama_client.requests.get") as blocked_mock:
        try:
            service.list_model_names()
            assert False, "Expected open breaker rejection"
        except OllamaUnavailable:
            pass
    assert blocked_mock.call_count == 0

    success = Mock()
    success.raise_for_status.return_value = None
    success.json.return_value = {"models": [{"name": "qwen3:4b"}]}
    with (
        patch("goat_ai.llm.ollama_client.time.monotonic", return_value=999.0),
        patch(
            "goat_ai.llm.ollama_client.requests.get", return_value=success
        ) as recovered_get,
    ):
        service._breaker_open_until_monotonic = 100.0
        names = service.list_model_names()

    assert names == ["qwen3:4b"]
    assert recovered_get.call_count == 1


def test_generate_completion_queues_fifo_when_only_one_slot_allowed() -> None:
    base = _settings(ttl=60)
    service = OllamaService(
        Settings(**{**base.__dict__, "ollama_max_concurrent_requests": 1})
    )

    started: list[str] = []
    finished: list[str] = []
    lock = threading.Lock()
    first_started = threading.Event()
    allow_first_finish = threading.Event()
    second_started = threading.Event()
    allow_second_finish = threading.Event()

    def _fake_post(*_args, **_kwargs):
        response = Mock()
        response.raise_for_status.return_value = None
        with lock:
            call_name = f"call-{len(started) + 1}"
            started.append(call_name)
        if call_name == "call-1":
            first_started.set()
            allow_first_finish.wait(timeout=2)
        elif call_name == "call-2":
            second_started.set()
            allow_second_finish.wait(timeout=2)
        response.json.return_value = {"response": call_name}
        finished.append(call_name)
        return response

    results: list[str] = []

    def _run_completion() -> None:
        results.append(service.generate_completion("qwen3:4b", "hello"))

    with patch("goat_ai.llm.ollama_client.requests.post", side_effect=_fake_post):
        thread_one = threading.Thread(target=_run_completion)
        thread_two = threading.Thread(target=_run_completion)

        thread_one.start()
        assert first_started.wait(timeout=2)
        thread_two.start()
        time.sleep(0.2)
        assert not second_started.is_set()

        allow_first_finish.set()
        thread_one.join(timeout=2)

        assert second_started.wait(timeout=2)
        allow_second_finish.set()
        thread_two.join(timeout=2)

    assert results == ["call-1", "call-2"]
    assert started == ["call-1", "call-2"]
    assert finished == ["call-1", "call-2"]


def test_generate_completion_allows_two_concurrent_requests_and_queues_third() -> None:
    service = OllamaService(_settings(ttl=60))

    started: list[str] = []
    lock = threading.Lock()
    first_started = threading.Event()
    second_started = threading.Event()
    third_started = threading.Event()
    release_first_two = threading.Event()
    release_third = threading.Event()

    def _fake_post(*_args, **_kwargs):
        response = Mock()
        response.raise_for_status.return_value = None
        with lock:
            call_name = f"call-{len(started) + 1}"
            started.append(call_name)
        if call_name == "call-1":
            first_started.set()
            release_first_two.wait(timeout=2)
        elif call_name == "call-2":
            second_started.set()
            release_first_two.wait(timeout=2)
        elif call_name == "call-3":
            third_started.set()
            release_third.wait(timeout=2)
        response.json.return_value = {"response": call_name}
        return response

    results: list[str] = []

    def _run_completion() -> None:
        results.append(service.generate_completion("qwen3:4b", "hello"))

    with patch("goat_ai.llm.ollama_client.requests.post", side_effect=_fake_post):
        threads = [threading.Thread(target=_run_completion) for _ in range(3)]
        threads[0].start()
        threads[1].start()
        assert first_started.wait(timeout=2)
        assert second_started.wait(timeout=2)

        threads[2].start()
        time.sleep(0.2)
        assert not third_started.is_set()

        release_first_two.set()
        assert third_started.wait(timeout=2)
        release_third.set()

        for thread in threads:
            thread.join(timeout=2)

    assert started == ["call-1", "call-2", "call-3"]
    assert sorted(results) == ["call-1", "call-2", "call-3"]
