"""POST /api/chat — streaming chat completion via Server-Sent Events."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from backend.config import get_settings
from backend.dependencies import get_llm_client
from backend.models.chat import ChatRequest
from backend.services.chat_service import stream_chat_sse
from goat_ai.config import Settings
from goat_ai.ollama_client import LLMClient

logger = logging.getLogger(__name__)
router = APIRouter()

_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",  # Disable nginx response buffering
    "Connection": "keep-alive",
}


@router.post("/chat")
def chat_stream(
    request: Request,
    req: ChatRequest,
    llm: LLMClient = Depends(get_llm_client),
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    """Stream an LLM response as Server-Sent Events.

    Each SSE event carries a JSON-encoded token string.
    The final event is ``data: "[DONE]"\\n\\n``.
    The client reads events with the native ``EventSource`` API or a fetch+ReadableStream.
    """
    client_ip: str = request.client.host if request.client else "unknown"
    user_name: str = request.headers.get("x-user-name", "").strip()
    return StreamingResponse(
        stream_chat_sse(
            llm=llm,
            model=req.model,
            messages=req.messages,
            system_prompt=settings.system_prompt,
            ip=client_ip,
            log_db_path=settings.log_db_path,
            user_name=user_name,
            session_id=req.session_id,
            all_messages=req.messages,
        ),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )
