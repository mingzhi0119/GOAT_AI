"""Versioned chart spec models; chart intent lives in ``goat_ai.chart_intent_v2``."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from goat_ai.chart_intent_v2 import (
    AggregateOp,
    ChartIntentFilterV2,
    ChartIntentSeriesV2,
    ChartIntentV2,
    ChartKind,
    SortDirection,
    TimeGrain,
)

ChartEngine = Literal["echarts"]


class ChartMetaV2(BaseModel):
    """Backend-generated metadata describing compilation/runtime behavior."""

    row_count: int
    truncated: bool = False
    warnings: list[str] = Field(default_factory=list)
    source_columns: list[str] = Field(default_factory=list)


class ChartSpecV2(BaseModel):
    """Compiled Apache ECharts chart payload sent to the frontend."""

    version: Literal["2.0"] = "2.0"
    engine: ChartEngine = "echarts"
    kind: ChartKind
    title: str
    description: str = ""
    dataset: list[dict[str, object]]
    option: dict[str, object]
    meta: ChartMetaV2


__all__ = [
    "AggregateOp",
    "ChartEngine",
    "ChartIntentFilterV2",
    "ChartIntentSeriesV2",
    "ChartIntentV2",
    "ChartKind",
    "ChartMetaV2",
    "ChartSpecV2",
    "SortDirection",
    "TimeGrain",
]
