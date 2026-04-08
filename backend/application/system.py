"""System use cases for telemetry, readiness, and feature gates."""
from __future__ import annotations

from fastapi.responses import JSONResponse, PlainTextResponse

from backend.application.ports import Settings
from backend.models.system import GPUStatusResponse, InferenceLatencyResponse, RuntimeTargetResponse, SystemFeaturesResponse
from backend.prometheus_metrics import render_prometheus_text
from backend.readiness_service import evaluate_readiness
from backend.services.gpu_service import read_gpu_status as _read_gpu_status
from backend.services.system_telemetry_service import (
    build_inference_latency_response,
    build_runtime_target_response,
    build_system_features_response,
)


def get_gpu_status(settings: Settings) -> GPUStatusResponse:
    return _read_gpu_status(settings)


def get_inference_latency() -> InferenceLatencyResponse:
    return build_inference_latency_response()


def get_system_features(settings: Settings) -> SystemFeaturesResponse:
    return build_system_features_response(settings)


def get_runtime_target(settings: Settings) -> RuntimeTargetResponse:
    return build_runtime_target_response(settings)


def get_ready(settings: Settings) -> JSONResponse:
    body, status = evaluate_readiness(settings)
    return JSONResponse(status_code=status, content=body)


def get_system_metrics() -> PlainTextResponse:
    return PlainTextResponse(
        render_prometheus_text(),
        media_type="text/plain; charset=utf-8",
    )
