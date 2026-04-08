"""Backend-facing type aliases re-exported for router signatures.

Routers must not import ``goat_ai`` directly; use this module for ``Settings`` and
``LLMClient`` annotations. Enforcement: ``lint-imports`` (see ``pyproject.toml``).
"""
from __future__ import annotations

from goat_ai.config import Settings
from goat_ai.ollama_client import LLMClient

__all__ = ["LLMClient", "Settings"]
