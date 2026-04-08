from __future__ import annotations

from typing import Sequence

import pandas as pd

from goat_ai.types import ChatTurn

# Marker used by the backend to embed the raw CSV data inside the file-context
# prompt so that tabular extractors can reconstruct a DataFrame from history.
CHART_DATA_CSV_MARKER = "CHART_DATA_CSV"
_CSV_EMBED_MARKER = CHART_DATA_CSV_MARKER

FILE_CONTEXT_UPLOAD_PREFIX = "[User uploaded tabular data for analysis]"
# Substring used to locate embedded CSV in user content (legacy wire + sniff fallback).
LEGACY_CSV_FENCE_SUBSTRING = f"{CHART_DATA_CSV_MARKER}:\n```\n"

# Instructions appended to every file-context prompt that explain the :::chart
# structured-output protocol to the LLM.
_CHART_INSTRUCTIONS = """\
VISUALIZATION PROTOCOL (read carefully):
When visualization is appropriate, append ONE JSON block at the very end of your \
response — after all prose — using EXACTLY this format, with no text after it:

:::chart
{"type":"line","title":"<short title>","xKey":"<column>","series":[{"key":"<column>","name":"<label>"}]}
:::

Rules:
- Use only column names listed in "Column names" above.
- Use "line" for trends / time-series, "bar" for category comparisons.
- Include 1–3 series keys maximum.
- Omit the block entirely if no chart is needed.
- Do NOT draw an ASCII chart; the system renders the chart automatically from the JSON.
"""


def describe_dataframe(df: pd.DataFrame) -> str:
    """Structured summary for prompt injection.

    Includes a compact CSV block (up to 30 rows) under the ``CHART_DATA_CSV``
    marker so the backend chart extractor can reconstruct the DataFrame from
    the conversation history without a separate file cache.
    """
    csv_rows = df.head(30).to_csv(index=False).strip()
    lines = [
        f"Dataframe shape: {df.shape[0]} rows × {df.shape[1]} columns.",
        f"Column names: {', '.join(map(str, df.columns.tolist()))}.",
        f"dtypes:\n{df.dtypes.to_string()}",
        f"Missing values per column:\n{df.isna().sum().to_string()}",
        f"Sample (first 5 rows):\n{df.head(5).to_string()}",
        f"\n{_CSV_EMBED_MARKER}:\n```\n{csv_rows}\n```",
    ]
    return "\n".join(lines)


def build_analysis_user_message(df: pd.DataFrame) -> str:
    """Build the hidden file-context user message injected at position 0 of the history."""
    return (
        f"{FILE_CONTEXT_UPLOAD_PREFIX}\n\n"
        f"{describe_dataframe(df)}\n\n"
        "Summarize what this data contains and suggest sensible next analyses. "
        "Cite the row/column counts in your answer."
    )


def messages_for_ollama(
    state_messages: Sequence[ChatTurn],
    system_prompt: str,
) -> list[dict[str, str]]:
    """Build Ollama /api/chat payload: system + user/assistant turns."""
    out: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    for m in state_messages:
        role = m.get("role")
        content = m.get("content", "")
        if role in ("user", "assistant") and isinstance(content, str):
            out.append({"role": role, "content": content})
    return out


def conversation_transcript(state_messages: Sequence[ChatTurn]) -> str:
    """Flatten history for /api/generate when chat API is disabled."""
    parts: list[str] = []
    for m in state_messages:
        role = m.get("role")
        content = m.get("content", "")
        if role == "user":
            parts.append(f"User: {content}")
        elif role == "assistant":
            parts.append(f"Assistant: {content}")
    return "\n\n".join(parts)
