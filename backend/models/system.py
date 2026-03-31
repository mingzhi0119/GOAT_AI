"""Pydantic schemas for system telemetry endpoints."""
from __future__ import annotations

from pydantic import BaseModel


class GPUStatusResponse(BaseModel):
    """GPU telemetry payload used by sidebar status strip."""

    available: bool
    active: bool
    message: str
    name: str = ""
    uuid: str = ""
    utilization_gpu: float | None = None
    memory_used_mb: float | None = None
    memory_total_mb: float | None = None
    temperature_c: float | None = None
    power_draw_w: float | None = None
