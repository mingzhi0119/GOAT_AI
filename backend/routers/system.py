"""System router — telemetry endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.config import BACKEND_HOST, BACKEND_PORT, get_settings
from backend.models.common import ErrorResponse
from backend.models.system import GPUStatusResponse, InferenceLatencyResponse, RuntimeTargetResponse
from backend.services.gpu_service import read_gpu_status
from goat_ai.config import Settings
from goat_ai.latency_metrics import get_inference_snapshot
from goat_ai.runtime_target import current_runtime_target, ordered_runtime_targets

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


@router.get(
    "/system/runtime-target",
    response_model=RuntimeTargetResponse,
    summary="Read resolved deployment target order",
    responses={401: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
def get_runtime_target(settings: Settings = Depends(get_settings)) -> RuntimeTargetResponse:
    """Return the current runtime target and the ordered deployment fallback list."""
    current = current_runtime_target(
        settings,
        current_port=BACKEND_PORT,
        host="127.0.0.1" if BACKEND_HOST == "0.0.0.0" else BACKEND_HOST,
    )
    ordered = ordered_runtime_targets(settings)
    return RuntimeTargetResponse(
        deploy_target=settings.deploy_target,
        current=current.__dict__,
        ordered_targets=[item.__dict__ for item in ordered],
    )
