"""Upload service — adapts FastAPI UploadFile to the goat_ai upload layer."""
from __future__ import annotations

import io
import json
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
    # Emit structured context so frontend can persist uploaded-file context.
    yield f'data: {json.dumps({"type": "file_context", "filename": filename, "prompt": analysis_prompt})}\n\n'
    chart_spec = _build_chart_spec(result)
    if chart_spec is not None:
        yield f'data: {json.dumps({"type": "chart_spec", "chart": chart_spec})}\n\n'

    from backend.models.chat import ChatMessage  # local import avoids circular dep
    chat_messages = [ChatMessage(role="user", content=analysis_prompt)]
    yield from stream_chat_sse(
        llm=llm,
        model=model,
        messages=chat_messages,
        system_prompt=settings.system_prompt,
        ip="upload",
        log_db_path=settings.log_db_path,
    )
