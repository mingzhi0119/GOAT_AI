"""Regression: think belongs at the Ollama request's top level on every path."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from goat_ai.config.settings import Settings
from goat_ai.llm.ollama_client import OllamaService, _apply_generation_options


def settings() -> Settings:
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
    )


@pytest.mark.parametrize("think", [False, True, "low", "medium", "high"])
@pytest.mark.parametrize("path", ["chat", "generate", "completion", "tools", "plan"])
def test_all_paths_forward_think_at_top_level(think: bool | str, path: str) -> None:
    service = OllamaService(settings())
    response = Mock()
    response.raise_for_status.return_value = None
    response.iter_lines.return_value = []
    response.json.return_value = {"response": "ok", "message": {"content": "ok"}}
    options = {"think": think, "temperature": 0.2, "num_predict": 128}
    with patch(
        "goat_ai.llm.ollama_client.requests.post", return_value=response
    ) as post:
        if path == "chat":
            list(service.yield_chat_tokens("qwen3:4b", [], ollama_options=options))
        elif path == "generate":
            list(
                service.yield_generate_tokens(
                    "qwen3:4b", "hello", ollama_options=options
                )
            )
        elif path == "completion":
            service.generate_completion("qwen3:4b", "hello", ollama_options=options)
        elif path == "tools":
            list(
                service.stream_tokens_with_tools(
                    "qwen3:4b", [], "hello", tools=[], ollama_options=options
                )
            )
        else:
            service.plan_tool_call(
                "qwen3:4b", [], "hello", tools=[], ollama_options=options
            )
    payload = post.call_args.kwargs["json"]
    assert payload["think"] == think
    assert payload["options"] == {"temperature": 0.2, "num_predict": 128}
    assert options["think"] == think  # Do not mutate caller-owned options.


def test_absent_or_only_think_does_not_add_empty_options() -> None:
    payload: dict[str, object] = {"model": "m"}
    _apply_generation_options(payload, None)
    assert payload == {"model": "m"}
    _apply_generation_options(payload, {"think": False})
    assert payload == {"model": "m", "think": False}
