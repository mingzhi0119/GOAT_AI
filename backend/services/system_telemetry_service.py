"""System telemetry assembly for HTTP APIs (latency snapshot, runtime target resolution)."""

from __future__ import annotations

import os

from backend.platform.config import BACKEND_HOST, BACKEND_PORT
from backend.domain.authz_types import AuthorizationContext
from backend.models.system import (
    CodeSandboxFeaturePayload,
    DesktopDiagnosticsResponse,
    InferenceLatencyResponse,
    RuntimeFeaturePayload,
    RuntimeOperationalContractResponse,
    RuntimeTargetItemResponse,
    RuntimeTargetResponse,
    SystemFeaturesResponse,
    WorkbenchFeaturePayload,
)
from backend.platform.readiness_service import evaluate_readiness
from backend.services.feature_gate_service import code_sandbox_policy_allowed
from backend.services.workbench_source_registry import list_workbench_sources
from backend.types import Settings
from goat_ai.config.feature_gate_reasons import RUNTIME_NOT_IMPLEMENTED
from goat_ai.config.feature_gates import (
    RuntimeFeatureSnapshot,
    compute_agent_workbench_snapshot,
    compute_code_sandbox_snapshot,
)
from goat_ai.telemetry.latency_metrics import get_inference_snapshot
from goat_ai.runtime.runtime_target import (
    current_runtime_target,
    ordered_runtime_targets,
)

_DESKTOP_APP_DATA_ENV = "GOAT_DESKTOP_APP_DATA_DIR"
_DESKTOP_SHELL_LOG_ENV = "GOAT_DESKTOP_SHELL_LOG_PATH"


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
    visible_sources = list_workbench_sources(
        settings=settings,
        auth_context=auth_context,
    )

    def _runtime_payload(snapshot: RuntimeFeatureSnapshot) -> RuntimeFeaturePayload:
        return RuntimeFeaturePayload(
            allowed_by_config=snapshot.allowed_by_config,
            available_on_host=snapshot.available_on_host,
            effective_enabled=snapshot.effective_enabled,
            deny_reason=snapshot.deny_reason,
        )

    def _workbench_capability(
        *,
        runtime_ready: bool,
        deny_reason: str | None = None,
    ) -> RuntimeFeaturePayload:
        if not workbench.allowed_by_config:
            return _runtime_payload(workbench)
        return RuntimeFeaturePayload(
            allowed_by_config=True,
            available_on_host=runtime_ready,
            effective_enabled=workbench.effective_enabled and runtime_ready,
            deny_reason=None
            if runtime_ready
            else (deny_reason or RUNTIME_NOT_IMPLEMENTED),
        )

    def _has_runnable_source(task_kind: str) -> bool:
        return any(
            source.runtime_ready and task_kind in source.task_kinds
            for source in visible_sources
        )

    return SystemFeaturesResponse(
        code_sandbox=CodeSandboxFeaturePayload(
            policy_allowed=code_sandbox_policy_allowed(auth_context),
            allowed_by_config=snap.allowed_by_config,
            available_on_host=snap.available_on_host,
            effective_enabled=snap.effective_enabled,
            provider_name=snap.provider_name,
            isolation_level=snap.isolation_level,
            network_policy_enforced=snap.network_policy_enforced,
            deny_reason=snap.deny_reason,
        ),
        workbench=WorkbenchFeaturePayload(
            agent_tasks=_runtime_payload(workbench),
            plan_mode=_runtime_payload(workbench),
            browse=_workbench_capability(runtime_ready=_has_runnable_source("browse")),
            deep_research=_workbench_capability(
                runtime_ready=_has_runnable_source("deep_research")
            ),
            artifact_workspace=_workbench_capability(runtime_ready=True),
            project_memory=_workbench_capability(runtime_ready=False),
            connectors=_workbench_capability(
                runtime_ready=any(
                    source.runtime_ready and source.kind == "connector"
                    for source in visible_sources
                )
            ),
        ),
    )


def build_desktop_diagnostics_response(
    settings: Settings,
    auth_context: AuthorizationContext,
) -> DesktopDiagnosticsResponse:
    """Return a desktop-scoped diagnostics snapshot for the settings surface."""
    app_data_dir = os.environ.get(_DESKTOP_APP_DATA_ENV, "").strip()
    if not app_data_dir:
        return DesktopDiagnosticsResponse(desktop_mode=False)

    runtime = build_runtime_target_response(settings)
    readiness_body, _status = evaluate_readiness(settings)
    features = build_system_features_response(settings, auth_context)
    checks = readiness_body.get("checks", {})
    failing_checks = [
        name
        for name, payload in checks.items()
        if isinstance(payload, dict) and payload.get("ok") is False
    ]
    skipped_checks = [
        name
        for name, payload in checks.items()
        if isinstance(payload, dict) and payload.get("skipped") is True
    ]

    return DesktopDiagnosticsResponse(
        desktop_mode=True,
        backend_base_url=runtime.current.base_url,
        readiness_ok=bool(readiness_body.get("ready")),
        failing_checks=failing_checks,
        skipped_checks=skipped_checks,
        code_sandbox_effective_enabled=features.code_sandbox.effective_enabled,
        workbench_effective_enabled=features.workbench.agent_tasks.effective_enabled,
        app_data_dir=app_data_dir,
        runtime_root=str(settings.runtime_root),
        data_dir=str(settings.data_dir),
        log_dir=str(settings.log_dir),
        log_db_path=str(settings.log_db_path),
        packaged_shell_log_path=os.environ.get(_DESKTOP_SHELL_LOG_ENV, "").strip()
        or None,
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
        operational_contract=RuntimeOperationalContractResponse(
            storage_model="sqlite-first",
            concurrency_model="single-writer",
            process_local_seams=[
                "rate_limiting",
                "background_jobs",
                "latency_metrics",
            ],
            scaling_notes=[
                "Keep one writable app process for SQLite-backed state.",
                "Per-process rate limits do not provide a global quota without external coordination.",
                "Aggregate latency and Prometheus metrics across instances externally when running more than one process.",
            ],
        ),
    )
