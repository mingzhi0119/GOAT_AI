from __future__ import annotations

from typing import Sequence

import pandas as pd

from goat_ai.types import ChatTurn


def describe_dataframe(df: pd.DataFrame) -> str:
    """Structured summary for prompt injection (grounding without a second agent framework)."""
    lines = [
        f"Dataframe shape: {df.shape[0]} rows × {df.shape[1]} columns.",
        f"Column names: {', '.join(map(str, df.columns.tolist()))}.",
        f"dtypes:\n{df.dtypes.to_string()}",
        f"Missing values per column:\n{df.isna().sum().to_string()}",
        f"Sample (first 5 rows):\n{df.head(5).to_string()}",
    ]
    return "\n".join(lines)


def build_analysis_user_message(df: pd.DataFrame) -> str:
    return (
        "[User requested analysis of uploaded tabular data]\n\n"
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
