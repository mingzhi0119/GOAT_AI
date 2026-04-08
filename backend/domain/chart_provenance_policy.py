"""Resolve chart data provenance (uploaded vs demo vs none) for tools and persistence."""
from __future__ import annotations

import pandas as pd

from backend.domain.chart_types import ChartDataSource


def default_demo_chart_dataframe() -> pd.DataFrame:
    """Small fallback dataset for chart tool calls when the user did not upload tabular data."""
    return pd.DataFrame(
        [
            {"category": "A", "value": 42, "revenue": 120, "cost": 70, "month": "Jan"},
            {"category": "B", "value": 28, "revenue": 95, "cost": 60, "month": "Feb"},
            {"category": "C", "value": 18, "revenue": 80, "cost": 55, "month": "Mar"},
            {"category": "D", "value": 12, "revenue": 72, "cost": 48, "month": "Apr"},
        ]
    )


def resolve_dataframe_for_native_chart_tool(
    uploaded: pd.DataFrame | None,
) -> tuple[pd.DataFrame, ChartDataSource]:
    """Return dataframe and source for native chart tool path (or demo fallback)."""
    if uploaded is not None:
        return uploaded, "uploaded"
    return default_demo_chart_dataframe(), "demo"


def resolve_chart_data_source_for_persist(
    *,
    declared: ChartDataSource,
    has_file_context_message: bool,
) -> ChartDataSource:
    """Upgrade ``none`` → ``uploaded`` when file-context rows exist (session upsert)."""
    if declared == "none" and has_file_context_message:
        return "uploaded"
    return declared
