"""Upload service for parsing CSV/XLSX files into reusable file-context SSE events."""
from __future__ import annotations

import io
import logging
from typing import Generator

from backend.services.sse import sse_done_event, sse_error_event, sse_event
from goat_ai.config import Settings
from goat_ai.tools import build_analysis_user_message
from goat_ai.uploads import TabularLoadResult, load_tabular_upload

logger = logging.getLogger(__name__)


class _UploadAdapter(io.BytesIO):
    """Wrap raw bytes with the file metadata required by TabularUploadLike."""

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
    content: bytes,
    filename: str,
    settings: Settings,
) -> Generator[str, None, None]:
    """Parse the uploaded file and emit file-context SSE metadata only.

    Uploading a file no longer emits a starter chart. The frontend should wait
    for a later LLM tool call before rendering any chart.
    """
    result = parse_upload(content, filename, settings)

    if result.user_error:
        yield sse_error_event(result.user_error)
        yield sse_done_event()
        return

    assert result.dataframe is not None  # parse_upload guarantees this when no user_error
    analysis_prompt = build_analysis_user_message(result.dataframe)
    yield sse_event({"type": "file_context", "filename": filename, "prompt": analysis_prompt})
    yield sse_done_event()


def analyze_upload(
    *,
    content: bytes,
    filename: str,
    settings: Settings,
) -> tuple[str, None]:
    """Parse the uploaded file and return reusable prompt metadata only."""
    result = parse_upload(content, filename, settings)
    if result.user_error:
        raise ValueError(result.user_error)

    assert result.dataframe is not None
    analysis_prompt = build_analysis_user_message(result.dataframe)
    return analysis_prompt, None
