"""System router — telemetry endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.config import get_settings
from backend.models.common import ErrorResponse
from backend.models.system import GPUStatusResponse, InferenceLatencyResponse
from backend.services.gpu_service import read_gpu_status
from goat_ai.config import Settings
from goat_ai.latency_metrics import get_inference_snapshot

router = APIRouter()


@router.get(
    "/system/gpu",
    response_model=GPUStatusResponse,
    summary="Read GPU telemetry",
    responses={401: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
def get_gpu_status(settings: Settings = Depends(get_settings)) -> GPUStatusResponse:
    """Return real-time GPU telemetry used by frontend status strip."""
    return read_gpu_status(settings)


@router.get(
    "/system/inference",
    response_model=InferenceLatencyResponse,
    summary="Read rolling chat latency telemetry",
    responses={401: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
def get_inference_latency() -> InferenceLatencyResponse:
    """Rolling average duration of completed chat streams (milliseconds)."""
    snap = get_inference_snapshot()
    return InferenceLatencyResponse(
        chat_avg_ms=float(snap["chat_avg_ms"]),
        chat_sample_count=int(snap["chat_sample_count"]),
    )
