"""Upload service — parses CSV/XLSX and emits structured SSE metadata events.

No LLM inference is triggered here. The backend returns:
  1. A ``file_context`` event so the frontend can persist the data description.
  2. An optional ``chart_spec`` event when numeric columns are present.
  3. A ``[DONE]`` sentinel to close the stream.

The user then types a follow-up question in the chat input; ``sendMessage``
prepends the file-context prompt to the conversation history so the model
answers with full awareness of the uploaded data.
"""
from __future__ import annotations

import json
import logging
from typing import Generator

from backend.services.chat_service import sse_event
from goat_ai.config import Settings
from goat_ai.tools import build_analysis_user_message
from goat_ai.uploads import TabularLoadResult, load_tabular_upload
import io

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


def _build_chart_spec(result: TabularLoadResult) -> dict[str, object] | None:
    """Build a simple chart spec from parsed dataframe when possible."""
    if result.dataframe is None:
        return None
    df = result.dataframe.head(20)
    if df.empty:
        return None
    numeric_cols = [
        col
        for col in df.columns
        if str(df[col].dtype).startswith(("int", "float"))
    ]
    if not numeric_cols:
        return None
    x_key = str(df.columns[0])
    y_col = str(numeric_cols[0])
    if y_col == x_key:
        y_col = str(numeric_cols[1]) if len(numeric_cols) > 1 else y_col
    cols = [x_key] if y_col == x_key else [x_key, y_col]
    data = df.loc[:, cols].fillna("").to_dict(orient="records")
    return {
        "type": "line",
        "title": f"{y_col} trend",
        "xKey": x_key,
        "series": [{"key": y_col, "name": y_col}],
        "data": data,
    }


def stream_upload_analysis_sse(
    *,
    content: bytes,
    filename: str,
    settings: Settings,
) -> Generator[str, None, None]:
    """Parse the uploaded file and emit structured SSE metadata events.

    Yields a ``file_context`` event (always), an optional ``chart_spec`` event,
    then ``[DONE]``. Yields a single error event if the file is invalid.
    """
    result = parse_upload(content, filename, settings)

    if result.user_error:
        yield sse_event(f"[ERROR] {result.user_error}")
        yield sse_event("[DONE]")
        return

    assert result.dataframe is not None  # parse_upload guarantees this when no user_error
    analysis_prompt = build_analysis_user_message(result.dataframe)
    yield f'data: {json.dumps({"type": "file_context", "filename": filename, "prompt": analysis_prompt})}\n\n'

    chart_spec = _build_chart_spec(result)
    if chart_spec is not None:
        yield f'data: {json.dumps({"type": "chart_spec", "chart": chart_spec})}\n\n'

    yield sse_event("[DONE]")


def analyze_upload(
    *,
    content: bytes,
    filename: str,
    settings: Settings,
) -> tuple[str, dict[str, object] | None]:
    """Parse the uploaded file and return a reusable prompt plus optional chart suggestion."""
    result = parse_upload(content, filename, settings)
    if result.user_error:
        raise ValueError(result.user_error)

    assert result.dataframe is not None
    analysis_prompt = build_analysis_user_message(result.dataframe)
    return analysis_prompt, _build_chart_spec(result)
