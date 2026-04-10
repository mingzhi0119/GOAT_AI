from __future__ import annotations

from unittest.mock import Mock, patch

from scripts.post_deploy_check import (
    _expect_chat_stream_contract,
    _expect_runtime_target,
    _parse_sse_events,
)


def test_parse_sse_events_extracts_json_frames() -> None:
    body = 'data: {"type":"token","token":"hi"}\n\ndata: {"type":"done"}\n\n'
    events = _parse_sse_events(body)
    assert [event["type"] for event in events] == ["token", "done"]


def test_expect_runtime_target_accepts_server_port() -> None:
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"ordered_targets": [{"port": 62606}]}
    with patch("scripts.post_deploy_check.requests.get", return_value=response):
        assert _expect_runtime_target("http://127.0.0.1:62606") == 0


def test_expect_chat_stream_contract_accepts_thinking_only_stream() -> None:
    model_response = Mock()
    model_response.raise_for_status.return_value = None
    model_response.json.return_value = {"models": ["qwen3:latest"]}
    chat_response = Mock()
    chat_response.raise_for_status.return_value = None
    chat_response.text = (
        'data: {"type":"thinking","token":"reasoning…"}\n\n'
        'data: {"type":"done"}\n\n'
    )
    with (
        patch("scripts.post_deploy_check.requests.get", return_value=model_response),
        patch("scripts.post_deploy_check.requests.post", return_value=chat_response),
    ):
        assert _expect_chat_stream_contract("http://127.0.0.1:62606") == 0


def test_expect_chat_stream_contract_accepts_token_then_done() -> None:
    model_response = Mock()
    model_response.raise_for_status.return_value = None
    model_response.json.return_value = {"models": ["tinyllama:latest"]}
    chat_response = Mock()
    chat_response.raise_for_status.return_value = None
    chat_response.text = 'data: {"type":"token","token":"hello"}\n\ndata: {"type":"done"}\n\n'
    with (
        patch("scripts.post_deploy_check.requests.get", return_value=model_response),
        patch("scripts.post_deploy_check.requests.post", return_value=chat_response) as post,
    ):
        assert _expect_chat_stream_contract("http://127.0.0.1:62606") == 0
    payload = post.call_args.kwargs["json"]
    assert payload["model"] == "tinyllama:latest"
    assert payload["think"] is False
    assert payload["max_tokens"] == 48
    assert payload["temperature"] == 0
