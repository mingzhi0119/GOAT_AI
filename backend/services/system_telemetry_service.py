"""System telemetry assembly for HTTP APIs (latency snapshot, runtime target resolution)."""

from __future__ import annotations

from backend.config import BACKEND_HOST, BACKEND_PORT
from backend.domain.authz_types import AuthorizationContext
from backend.models.system import (
    CodeSandboxFeaturePayload,
    InferenceLatencyResponse,
    RuntimeFeaturePayload,
    RuntimeTargetItemResponse,
    RuntimeTargetResponse,
    SystemFeaturesResponse,
    WorkbenchFeaturePayload,
)
from backend.services.feature_gate_service import code_sandbox_policy_allowed
from backend.types import Settings
from goat_ai.feature_gates import (
    RuntimeFeatureSnapshot,
    compute_agent_workbench_snapshot,
    compute_code_sandbox_snapshot,
)
from goat_ai.latency_metrics import get_inference_snapshot
from goat_ai.runtime_target import current_runtime_target, ordered_runtime_targets


def build_inference_latency_response() -> InferenceLatencyResponse:
    """Map in-process latency metrics into the API response model."""
    snap = get_inference_snapshot()
    return InferenceLatencyResponse(
        chat_avg_ms=float(snap["chat_avg_ms"]),
        chat_sample_count=int(snap["chat_sample_count"]),
        chat_p50_ms=float(snap["chat_p50_ms"]),
        chat_p95_ms=float(snap["chat_p95_ms"]),
        first_token_avg_ms=float(snap["first_token_avg_ms"]),
        first_token_sample_count=int(snap["first_token_sample_count"]),
        first_token_p50_ms=float(snap["first_token_p50_ms"]),
        first_token_p95_ms=float(snap["first_token_p95_ms"]),
        model_buckets=dict(snap["model_buckets"]),
    )


def build_system_features_response(
    settings: Settings,
    auth_context: AuthorizationContext,
) -> SystemFeaturesResponse:
    """Expose machine-readable capability flags for optional / high-risk features."""
    snap = compute_code_sandbox_snapshot(settings)
    workbench = compute_agent_workbench_snapshot(settings)

    def _runtime_payload(snapshot: RuntimeFeatureSnapshot) -> RuntimeFeaturePayload:
        return RuntimeFeaturePayload(
            allowed_by_config=snapshot.allowed_by_config,
            available_on_host=snapshot.available_on_host,
            effective_enabled=snapshot.effective_enabled,
            deny_reason=snapshot.deny_reason,
        )

    return SystemFeaturesResponse(
        code_sandbox=CodeSandboxFeaturePayload(
            policy_allowed=code_sandbox_policy_allowed(auth_context),
            allowed_by_config=snap.allowed_by_config,
            available_on_host=snap.available_on_host,
            effective_enabled=snap.effective_enabled,
            deny_reason=snap.deny_reason,
        ),
        workbench=WorkbenchFeaturePayload(
            agent_tasks=_runtime_payload(workbench),
            plan_mode=_runtime_payload(workbench),
            browse=_runtime_payload(workbench),
            deep_research=_runtime_payload(workbench),
            artifact_workspace=_runtime_payload(workbench),
            project_memory=_runtime_payload(workbench),
            connectors=_runtime_payload(workbench),
        ),
    )


def build_runtime_target_response(settings: Settings) -> RuntimeTargetResponse:
    """Resolve current and ordered runtime targets for deploy/ops and the status UI."""
    current = current_runtime_target(
        settings,
        current_port=BACKEND_PORT,
        host="127.0.0.1" if BACKEND_HOST == "0.0.0.0" else BACKEND_HOST,
    )
    ordered = ordered_runtime_targets(settings)
    return RuntimeTargetResponse(
        deploy_target=settings.deploy_target,
        current=RuntimeTargetItemResponse(**current.__dict__),
        ordered_targets=[
            RuntimeTargetItemResponse(**item.__dict__) for item in ordered
        ],
    )
