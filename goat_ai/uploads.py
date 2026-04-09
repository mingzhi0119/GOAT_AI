from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from goat_ai.config import Settings
from goat_ai.types import TabularUploadLike

logger = logging.getLogger(__name__)


@dataclass
class TabularLoadResult:
    """Outcome of parsing an uploaded CSV/XLSX."""

    dataframe: Optional[pd.DataFrame] = None
    user_error: Optional[str] = None
    log_event: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.dataframe is not None and self.user_error is None


def load_tabular_upload(
    uploaded_file: TabularUploadLike, settings: Settings
) -> TabularLoadResult:
    """Validate size/rows and load CSV or Excel into a DataFrame."""
    if uploaded_file.size > settings.max_upload_bytes:
        logger.warning("Upload rejected: size %s exceeds limit", uploaded_file.size)
        return TabularLoadResult(
            user_error=(
                f"File is too large ({uploaded_file.size / (1024 * 1024):.1f} MB). "
                f"Maximum allowed is {settings.max_upload_mb} MB."
            ),
            log_event="size_limit",
        )
    try:
        if uploaded_file.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
    except Exception:
        logger.exception("Failed to parse upload: %s", uploaded_file.name)
        return TabularLoadResult(
            user_error="Could not read this file. Please use a valid CSV or XLSX.",
            log_event="parse_error",
        )
    if len(df) > settings.max_dataframe_rows:
        logger.warning("Upload rejected: row count %s", len(df))
        return TabularLoadResult(
            user_error=(
                f"Too many rows ({len(df):,}). Maximum allowed is {settings.max_dataframe_rows:,}. "
                "Try sampling or splitting your data."
            ),
            log_event="row_limit",
        )
    return TabularLoadResult(dataframe=df)
