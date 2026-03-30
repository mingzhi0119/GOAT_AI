"""Upload service — adapts FastAPI UploadFile to the goat_ai upload layer."""
from __future__ import annotations

import io
import logging
from typing import Generator

from backend.services.chat_service import sse_event, stream_chat_sse
from goat_ai.config import Settings
from goat_ai.exceptions import OllamaUnavailable
from goat_ai.ollama_client import LLMClient
from goat_ai.tools import build_analysis_user_message
from goat_ai.types import ChatTurn
from goat_ai.uploads import TabularLoadResult, load_tabular_upload

logger = logging.getLogger(__name__)


class _UploadAdapter(io.BytesIO):
    """Wraps raw bytes with the name/size attributes required by TabularUploadLike."""

    def __init__(self, content: bytes, filename: str) -> None:
        super().__init__(content)
        self.name: str = filename
        self.size: int = len(content)


def parse_upload(content: bytes, filename: str, settings: Settings) -> TabularLoadResult:
    """Validate and parse raw upload bytes into a TabularLoadResult."""
    adapter = _UploadAdapter(content, filename)
    return load_tabular_upload(adapter, settings)


def stream_upload_analysis_sse(
    *,
    llm: LLMClient,
    model: str,
    content: bytes,
    filename: str,
    settings: Settings,
) -> Generator[str, None, None]:
    """Parse the uploaded file then stream an LLM analysis as SSE events.

    Yields a single error event (then [DONE]) if the file is invalid.
    """
    result = parse_upload(content, filename, settings)

    if result.user_error:
        yield sse_event(f"[ERROR] {result.user_error}")
        yield sse_event("[DONE]")
        return

    assert result.dataframe is not None  # parse_upload guarantees this when no user_error
    analysis_prompt = build_analysis_user_message(result.dataframe)
    messages = [{"role": "user", "content": analysis_prompt}]

    from backend.models.chat import ChatMessage  # local import avoids circular dep

    chat_messages = [ChatMessage(role="user", content=analysis_prompt)]
    yield from stream_chat_sse(
        llm=llm,
        model=model,
        messages=chat_messages,
        system_prompt=settings.system_prompt,
    )
