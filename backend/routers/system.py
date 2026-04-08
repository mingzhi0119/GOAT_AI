"""System router — telemetry endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, PlainTextResponse

from backend.config import get_settings
from backend.models.common import ErrorResponse
from backend.models.system import GPUStatusResponse, InferenceLatencyResponse, RuntimeTargetResponse
from backend.prometheus_metrics import render_prometheus_text
from backend.readiness_service import evaluate_readiness
from backend.services.gpu_service import read_gpu_status
from backend.services.system_telemetry_service import (
    build_inference_latency_response,
    build_runtime_target_response,
)
from backend.types import Settings

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
    return build_inference_latency_response()


@router.get(
    "/system/runtime-target",
    response_model=RuntimeTargetResponse,
    summary="Read resolved deployment target order",
    responses={401: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
def get_runtime_target(settings: Settings = Depends(get_settings)) -> RuntimeTargetResponse:
    """Return the current runtime target and the ordered deployment fallback list."""
    return build_runtime_target_response(settings)


@router.get(
    "/ready",
    summary="Readiness probe (SQLite + optional Ollama)",
    responses={503: {"description": "Not ready; see JSON ``checks`` for failing dependency."}},
)
def get_ready(settings: Settings = Depends(get_settings)) -> JSONResponse:
    """Return 200 when SQLite and (unless skipped) Ollama are reachable; 503 otherwise."""
    body, status = evaluate_readiness(settings)
    return JSONResponse(status_code=status, content=body)


@router.get(
    "/system/metrics",
    response_class=PlainTextResponse,
    summary="Prometheus text metrics",
    responses={401: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
def get_system_metrics() -> PlainTextResponse:
    """Expose in-process counters and histograms for Prometheus scraping."""
    return PlainTextResponse(
        render_prometheus_text(),
        media_type="text/plain; charset=utf-8",
    )
