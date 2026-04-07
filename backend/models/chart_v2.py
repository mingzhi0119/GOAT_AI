"""Versioned chart intent/spec models for the Apache ECharts migration."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ChartKind = Literal["line", "bar", "stacked_bar", "area", "scatter", "pie"]
AggregateOp = Literal["sum", "avg", "count", "min", "max", "none"]
TimeGrain = Literal["auto", "day", "week", "month", "quarter", "year", "none"]
SortDirection = Literal["asc", "desc", "none"]
ChartEngine = Literal["echarts"]


class ChartIntentSeriesV2(BaseModel):
    """One requested Y-series before backend compilation."""

    key: str
    name: str | None = None
    aggregate: AggregateOp = "none"


class ChartIntentFilterV2(BaseModel):
    """Optional high-level filter requested by the model."""

    column: str
    operator: Literal["eq", "neq", "gt", "gte", "lt", "lte", "in"]
    value: str | float | int | bool | list[str]


class ChartIntentV2(BaseModel):
    """Intermediate chart intent produced by native tool calling."""

    version: Literal["2.0"] = "2.0"
    chart_type: ChartKind
    title: str = Field(default="", max_length=120)
    description: str = Field(default="", max_length=400)
    x_key: str = Field(..., min_length=1)
    series: list[ChartIntentSeriesV2] = Field(default_factory=list, max_length=3)
    group_by: str | None = None
    time_grain: TimeGrain = "auto"
    stack: bool = False
    sort_by: str | None = None
    sort_direction: SortDirection = "none"
    top_n: int | None = Field(default=None, ge=1, le=50)
    filters: list[ChartIntentFilterV2] = Field(default_factory=list, max_length=5)


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
