"""Chart tool — builds ChartSpec payloads from LLM-chosen column selections.

Option A (structured output, current):
    The LLM emits a :::chart JSON block. The backend calls
    build_chart_spec_from_llm_selection() to attach real data rows and validate
    column names before emitting the chart_spec SSE event.

Option B (Ollama tool calling, future):
    GENERATE_CHART_SCHEMA provides the JSON schema that would be passed in the
    ``tools`` parameter of /api/chat. Only llama3.1+ models support this.
"""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# ── JSON schema for future Ollama tool calling (Option B) ─────────────────────
GENERATE_CHART_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "generate_chart",
        "description": (
            "Render a chart from the uploaded tabular data. "
            "Call this whenever the user asks to visualize, plot, or chart the data."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "chart_type": {
                    "type": "string",
                    "enum": ["line", "bar"],
                    "description": "Chart type — line for trends, bar for comparisons.",
                },
                "title": {
                    "type": "string",
                    "description": "Short chart title (max 60 chars).",
                },
                "x_key": {
                    "type": "string",
                    "description": "Column name for the X axis (usually time or category).",
                },
                "series": {
                    "type": "array",
                    "description": "One or more Y-axis series (max 3).",
                    "items": {
                        "type": "object",
                        "properties": {
                            "key": {"type": "string", "description": "Column name."},
                            "name": {"type": "string", "description": "Display label."},
                        },
                        "required": ["key", "name"],
                    },
                },
            },
            "required": ["chart_type", "title", "x_key", "series"],
        },
    },
}


def build_chart_spec_from_llm_selection(
    df: pd.DataFrame,
    x_key: str,
    series_keys: list[str],
    chart_type: str = "line",
    title: str = "",
) -> dict[str, object] | None:
    """Build a ChartSpec payload from LLM-chosen column names and the parsed DataFrame.

    Validates that all column names actually exist in the DataFrame before
    constructing the payload. Returns None when the selection is invalid so
    the caller can skip chart emission and fall back to text-only output.
    """
    available = set(df.columns.tolist())

    if x_key not in available:
        logger.warning("chart_tool: x_key %r not in DataFrame columns %r", x_key, list(available))
        return None

    valid_series = [k for k in series_keys if k in available and k != x_key]
    if not valid_series:
        logger.warning("chart_tool: no valid series keys in %r", series_keys)
        return None

    cols = [x_key] + valid_series
    data = df[cols].head(50).fillna("").to_dict(orient="records")

    safe_type = chart_type if chart_type in ("line", "bar") else "line"
    effective_title = title.strip() or f"{', '.join(valid_series)} trend"

    return {
        "type": safe_type,
        "title": effective_title,
        "xKey": x_key,
        "series": [{"key": k, "name": k} for k in valid_series],
        "data": data,
    }
