"""Backend-facing type aliases re-exported for router signatures.

Routers must not import ``goat_ai`` directly; use this module for ``Settings`` and
``LLMClient`` annotations. Enforcement: ``lint-imports`` (see ``pyproject.toml``).
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from goat_ai.config import Settings
from goat_ai.exceptions import OllamaUnavailable
from goat_ai.ollama_client import LLMClient


@runtime_checkable
class AsyncUploadReader(Protocol):
    """Async-read upload surface (matches Starlette/FastAPI ``UploadFile`` for typing)."""

    filename: str | None
    content_type: str | None

    async def read(self, size: int = -1) -> bytes: ...


__all__ = ["AsyncUploadReader", "LLMClient", "OllamaUnavailable", "Settings"]
