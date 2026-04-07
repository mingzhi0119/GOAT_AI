"""Pydantic schemas for upload analysis endpoints."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChartSeries(BaseModel):
    """One Y-axis series in a chart payload."""

    key: str
    name: str


class ChartSpec(BaseModel):
    """Structured chart payload consumed by the frontend."""

    type: Literal["line", "bar"]
    title: str
    xKey: str
    series: list[ChartSeries]
    data: list[dict[str, object]]


class UploadAnalysisResponse(BaseModel):
    """JSON response for POST /api/upload/analyze."""

    filename: str
    prompt: str = Field(..., description="Hidden analysis prompt derived from the uploaded table.")
    chart: ChartSpec | None = Field(
        default=None,
        description="Suggested starter chart when numeric columns are available.",
    )
