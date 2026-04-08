"""FastAPI dependency factories (Depends() callables).

Import these in routers; never instantiate services directly in route handlers.
"""
from __future__ import annotations

from fastapi import Depends

from backend.config import get_settings
from backend.services.chat_runtime import (
    ConversationLogger,
    OllamaTitleGenerator,
    SessionRepository,
    SQLiteConversationLogger,
    SQLiteSessionRepository,
    TitleGenerator,
)
from backend.services.tabular_context import EmbeddedCsvTabularExtractor, TabularContextExtractor
from backend.services.safeguard_service import RuleBasedSafeguardService, SafeguardService
from backend.types import LLMClient, Settings
from goat_ai.ollama_client import OllamaService


def get_llm_client(settings: Settings = Depends(get_settings)) -> LLMClient:
    """Return an OllamaService bound to the current settings.

    Returning the Protocol type (LLMClient) allows test code to inject fakes
    via app.dependency_overrides[get_llm_client] = lambda: FakeLLMClient().
    """
    return OllamaService(settings)


def get_conversation_logger(
    settings: Settings = Depends(get_settings),
) -> ConversationLogger:
    """Return the append-only conversation logger bound to current settings."""
    return SQLiteConversationLogger(settings.log_db_path)


def get_session_repository(
    settings: Settings = Depends(get_settings),
) -> SessionRepository:
    """Return the session repository bound to current settings."""
    return SQLiteSessionRepository(settings.log_db_path)


def get_title_generator(llm: LLMClient = Depends(get_llm_client)) -> TitleGenerator:
    """Return the title generator using the same Ollama client as chat (injectable for tests)."""
    return OllamaTitleGenerator(llm)


def get_tabular_context_extractor() -> TabularContextExtractor:
    """Return the tabular context extractor used for chart tool data resolution."""
    return EmbeddedCsvTabularExtractor()


def get_safeguard_service() -> SafeguardService:
    """Return the safeguard policy service used to moderate chat input/output."""
    return RuleBasedSafeguardService()
