"""Injectable boundary for resolving tabular data embedded in chat messages."""
from __future__ import annotations

import io
import logging
import re
from typing import Protocol

import pandas as pd

from backend.models.chat import ChatMessage
from goat_ai.tools import CHART_DATA_CSV_MARKER

logger = logging.getLogger(__name__)

_CSV_EMBED_RE = re.compile(
    re.escape(CHART_DATA_CSV_MARKER) + r":\n```\n(.*?)\n```",
    re.DOTALL,
)
LEGACY_CSV_FENCE_SUBSTRING = f"{CHART_DATA_CSV_MARKER}:\n```\n"


class TabularContextExtractor(Protocol):
    """Extract a pandas DataFrame from conversation context (e.g. upload-derived CSV)."""

    def extract_dataframe(self, messages: list[ChatMessage]) -> pd.DataFrame | None:
        """Return the first parsable embedded table from user messages, or None."""
        ...


class EmbeddedCsvTabularExtractor:
    """Legacy wire format: `CHART_DATA_CSV` fenced block inside user message content."""

    def extract_dataframe(self, messages: list[ChatMessage]) -> pd.DataFrame | None:
        for message in messages:
            if message.role != "user":
                continue
            match = _CSV_EMBED_RE.search(message.content)
            if match:
                try:
                    return pd.read_csv(io.StringIO(match.group(1)))
                except Exception:
                    logger.warning("Failed to parse embedded CSV from file-context message")
        return None
