"""POST /api/chat - streaming chat completion via Server-Sent Events."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from fastapi.responses import StreamingResponse

from backend.api_errors import AUTH_SESSION_OWNER_REQUIRED, build_error_body
from backend.application.chat import prepare_chat_request, stream_chat_response
from backend.application.exceptions import (
    ChatIdempotencyConflictError,
    ChatIdempotencyInProgressError,
    ChatKnowledgeImageConflictError,
    ChatOwnerRequiredError,
)
from backend.application.ports import (
    ChatCapacityError,
    ConversationLogger,
    LLMClient,
    OllamaUnavailable,
    SafeguardService,
    SessionRepository,
    Settings,
    TabularContextExtractor,
    TitleGenerator,
)
from backend.config import get_settings
from backend.dependencies import (
    get_conversation_logger,
    get_llm_client,
    get_safeguard_service,
    get_session_repository,
    get_tabular_context_extractor,
    get_title_generator,
)
from backend.models.chat import ChatRequest
from backend.models.common import ErrorResponse

logger = logging.getLogger(__name__)
router = APIRouter()


def _raise_owner_required(exc: ChatOwnerRequiredError) -> None:
    raise HTTPException(
        status_code=403,
        detail=build_error_body(
            detail=str(exc),
            code=AUTH_SESSION_OWNER_REQUIRED,
            status_code=403,
        ),
    ) from exc


@router.post(
    "/chat",
    summary="Stream a chat completion over SSE",
    responses={
        200: {"content": {"text/event-stream": {}}},
        401: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
def chat_stream(
    request: Request,
    req: ChatRequest,
    llm: LLMClient = Depends(get_llm_client),
    conversation_logger: ConversationLogger = Depends(get_conversation_logger),
    session_repository: SessionRepository = Depends(get_session_repository),
    title_generator: TitleGenerator = Depends(get_title_generator),
    tabular_extractor: TabularContextExtractor = Depends(get_tabular_context_extractor),
    safeguard_service: SafeguardService | None = Depends(get_safeguard_service),
    settings: Settings = Depends(get_settings),
    idempotency_key_header: str | None = Header(default=None, alias="Idempotency-Key"),
) -> StreamingResponse:
    """Stream an LLM response as Server-Sent Events."""
    client_ip: str = request.client.host if request.client else "unknown"
    user_name = request.headers.get("x-user-name", "").strip()
    idempotency_key = (idempotency_key_header or "").strip()
    session_owner_id = (request.headers.get("x-goat-owner-id") or "").strip()

    try:
        prepared = prepare_chat_request(
            req=req,
            settings=settings,
            llm=llm,
            session_owner_id=session_owner_id,
        )
        return stream_chat_response(
            req=req,
            prepared=prepared,
            client_ip=client_ip,
            user_name=user_name,
            llm=llm,
            conversation_logger=conversation_logger,
            session_repository=session_repository,
            title_generator=title_generator,
            tabular_extractor=tabular_extractor,
            safeguard_service=safeguard_service,
            settings=settings,
            idempotency_key=idempotency_key,
        )
    except ChatCapacityError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ChatKnowledgeImageConflictError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ChatOwnerRequiredError as exc:
        _raise_owner_required(exc)
    except ChatIdempotencyConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ChatIdempotencyInProgressError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except OllamaUnavailable as exc:
        logger.warning("Ollama unreachable during chat preflight: %s", exc)
        raise HTTPException(status_code=503, detail="AI backend unavailable") from exc
