"""System router - telemetry endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from backend.application.system import (
    get_gpu_status as read_gpu_status,
    get_inference_latency,
    get_ready,
    get_runtime_target,
    get_system_features,
    get_system_metrics,
)
from backend.domain.authz_types import AuthorizationContext
from backend.application.ports import Settings
from backend.platform.config import get_settings
from backend.platform.dependencies import get_authorization_context
from backend.models.common import ErrorResponse
from backend.models.system import (
    GPUStatusResponse,
    InferenceLatencyResponse,
    RuntimeTargetResponse,
    SystemFeaturesResponse,
)

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
def get_inference_latency_route() -> InferenceLatencyResponse:
    """Rolling average duration of completed chat streams (milliseconds)."""
    return get_inference_latency()


@router.get(
    "/system/features",
    response_model=SystemFeaturesResponse,
    summary="Read capability-gated feature flags",
    responses={401: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
def get_system_features_route(
    settings: Settings = Depends(get_settings),
    auth_context: AuthorizationContext = Depends(get_authorization_context),
) -> SystemFeaturesResponse:
    """Return config + host probes for optional high-risk features (see docs/standards/ENGINEERING_STANDARDS.md §15)."""
    return get_system_features(settings, auth_context)


@router.get(
    "/system/runtime-target",
    response_model=RuntimeTargetResponse,
    summary="Read resolved deployment target order",
    responses={401: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
def get_runtime_target_route(
    settings: Settings = Depends(get_settings),
) -> RuntimeTargetResponse:
    """Return the current runtime target and the ordered deployment fallback list."""
    return get_runtime_target(settings)


@router.get(
    "/ready",
    summary="Readiness probe (SQLite + optional Ollama)",
    responses={
        503: {"description": "Not ready; see JSON ``checks`` for failing dependency."}
    },
)
def get_ready_route(settings: Settings = Depends(get_settings)):
    """Return 200 when SQLite and (unless skipped) Ollama are reachable; 503 otherwise."""
    return get_ready(settings)


@router.get(
    "/system/metrics",
    response_class=PlainTextResponse,
    summary="Prometheus text metrics",
    responses={401: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
def get_system_metrics_route():
    """Expose in-process counters and histograms for Prometheus scraping."""
    return get_system_metrics()
