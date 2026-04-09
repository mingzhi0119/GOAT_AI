"""Helpers to map ChatRequest sampling fields to Ollama ``options``."""

from __future__ import annotations

from backend.models.chat import ChatRequest


def build_ollama_options(
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
    top_p: float | None = None,
) -> dict[str, float | int] | None:
    """Build Ollama ``options`` from optional fields; None if all unset."""
    opts: dict[str, float | int] = {}
    if temperature is not None:
        opts["temperature"] = temperature
    if max_tokens is not None:
        opts["num_predict"] = max_tokens
    if top_p is not None:
        opts["top_p"] = top_p
    return opts if opts else None


def ollama_options_from_chat_request(req: ChatRequest) -> dict[str, float | int] | None:
    """Build Ollama ``options`` from POST /api/chat body."""
    return build_ollama_options(
        temperature=req.temperature,
        max_tokens=req.max_tokens,
        top_p=req.top_p,
    )
