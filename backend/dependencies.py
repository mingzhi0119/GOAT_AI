"""FastAPI dependency factories (Depends() callables).

Import these in routers; never instantiate services directly in route handlers.
"""
from __future__ import annotations

from fastapi import Depends

from backend.config import get_settings
from goat_ai.config import Settings
from goat_ai.ollama_client import LLMClient, OllamaService


def get_llm_client(settings: Settings = Depends(get_settings)) -> LLMClient:
    """Return an OllamaService bound to the current settings.

    Returning the Protocol type (LLMClient) allows test code to inject fakes
    via app.dependency_overrides[get_llm_client] = lambda: FakeLLMClient().
    """
    return OllamaService(settings)
