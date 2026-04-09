"""FastAPI dependency factories (Depends() callables).

Import these in routers; never instantiate services directly in route handlers.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from backend.domain.authz_types import AuthorizationContext
from backend.domain.credential_registry import build_local_authorization_context
from backend.api_errors import AUTH_INVALID_API_KEY, build_error_body
from backend.config import get_settings
from backend.services.chat_runtime import (
    ConversationLogger,
    OllamaTitleGenerator,
    SessionRepository,
    SQLiteConversationLogger,
    SQLiteSessionRepository,
    TitleGenerator,
)
from backend.services.tabular_context import (
    EmbeddedCsvTabularExtractor,
    TabularContextExtractor,
)
from backend.services.safeguard_service import (
    ModeScopedSafeguardService,
    SafeguardService,
)
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


def get_authorization_context(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> AuthorizationContext:
    ctx = getattr(request.state, "authorization_context", None)
    if isinstance(ctx, AuthorizationContext):
        return ctx
    if not settings.api_key:
        return build_local_authorization_context()
    raise HTTPException(
        status_code=401,
        detail=build_error_body(
            detail="Invalid or missing API key.",
            code=AUTH_INVALID_API_KEY,
            status_code=401,
        ),
    )


def get_title_generator(llm: LLMClient = Depends(get_llm_client)) -> TitleGenerator:
    """Return the title generator using the same Ollama client as chat (injectable for tests)."""
    return OllamaTitleGenerator(llm)


def get_tabular_context_extractor() -> TabularContextExtractor:
    """Return the tabular context extractor used for chart tool data resolution."""
    return EmbeddedCsvTabularExtractor()


def get_safeguard_service(
    settings: Settings = Depends(get_settings),
) -> SafeguardService | None:
    """Return the active safeguard service, or None when moderation is disabled.

    Controlled by two env vars (see docs/OPERATIONS.md — Safeguard configuration):
      GOAT_SAFEGUARD_ENABLED=false  → always returns None (master kill-switch)
      GOAT_SAFEGUARD_MODE=off       → also returns None
      GOAT_SAFEGUARD_MODE=input_only|output_only|full → returns a ModeScopedSafeguardService

    Returning None is correct: chat_stream_service already guards every safeguard
    call with `if safeguard is None` checks, so None means "allow everything through"
    without any scattered conditionals in the calling code.
    """
    if not settings.safeguard_enabled or settings.safeguard_mode == "off":
        return None
    return ModeScopedSafeguardService(mode=settings.safeguard_mode)
