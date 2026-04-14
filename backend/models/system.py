"""Pydantic schemas for system telemetry endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field

from backend.models.code_sandbox import CodeSandboxIsolationLevel


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


class InferenceLatencyResponse(BaseModel):
    """Rolling average chat completion time (server-side, in-process)."""

    chat_avg_ms: float
    chat_sample_count: int
    chat_p50_ms: float
    chat_p95_ms: float
    first_token_avg_ms: float
    first_token_sample_count: int
    first_token_p50_ms: float
    first_token_p95_ms: float
    model_buckets: dict[str, dict[str, float | int]]


class RuntimeTargetItemResponse(BaseModel):
    """One runtime target candidate in deployment preference order."""

    mode: str
    host: str
    port: int
    base_url: str
    reason: str


class RuntimeOperationalContractResponse(BaseModel):
    """Operator-facing runtime contract for scaling and recovery expectations."""

    storage_model: str
    concurrency_model: str
    process_local_seams: list[str]
    scaling_notes: list[str]


class RuntimeTargetResponse(BaseModel):
    """Resolved runtime target metadata used by deploy/ops tooling."""

    deploy_mode: int
    deploy_mode_name: str
    current: RuntimeTargetItemResponse
    ordered_targets: list[RuntimeTargetItemResponse]
    operational_contract: RuntimeOperationalContractResponse


class CodeSandboxFeaturePayload(BaseModel):
    """Runtime / dependency readiness for the code sandbox (§15).

    ``policy_allowed`` is evaluated from the current request's authorization context.
    Runtime availability remains separate and must not be conflated with policy denial.
    """

    policy_allowed: bool = Field(
        description="Caller-scoped policy gate derived from credential scopes."
    )
    allowed_by_config: bool = Field(
        description="Operator enabled the feature in deployment config."
    )
    available_on_host: bool = Field(
        description="Probed runtime dependency (e.g. Docker) appears usable."
    )
    effective_enabled: bool = Field(description="Both config and probe satisfied.")
    provider_name: str = Field(
        description="Selected runtime provider for code sandbox execution."
    )
    isolation_level: CodeSandboxIsolationLevel = Field(
        description="Isolation tier for the active provider: container or host."
    )
    network_policy_enforced: bool = Field(
        description="Whether the selected provider can actually enforce the declared network policy."
    )
    deny_reason: str | None = Field(
        default=None,
        description="Controlled enum for runtime gate only; never raw exception text.",
    )


class RuntimeFeaturePayload(BaseModel):
    """Runtime / dependency readiness for optional non-policy-gated features."""

    allowed_by_config: bool = Field(
        description="Operator enabled the feature family in deployment config."
    )
    available_on_host: bool = Field(
        description="Required runtime dependencies and executors are available."
    )
    effective_enabled: bool = Field(description="Both config and runtime are ready.")
    deny_reason: str | None = Field(
        default=None,
        description="Controlled enum for runtime gate only; never raw exception text.",
    )


class WorkbenchFeaturePayload(BaseModel):
    """Capability inventory for future agent/workbench surfaces."""

    agent_tasks: RuntimeFeaturePayload
    plan_mode: RuntimeFeaturePayload
    browse: RuntimeFeaturePayload
    deep_research: RuntimeFeaturePayload
    artifact_workspace: RuntimeFeaturePayload
    artifact_exports: RuntimeFeaturePayload
    project_memory: RuntimeFeaturePayload
    connectors: RuntimeFeaturePayload


class SystemFeaturesResponse(BaseModel):
    """Public feature flags derived from config + host probes."""

    code_sandbox: CodeSandboxFeaturePayload
    workbench: WorkbenchFeaturePayload


class DesktopDiagnosticsResponse(BaseModel):
    """Desktop-only runtime diagnostics used by the settings panel."""

    desktop_mode: bool
    backend_base_url: str | None = None
    readiness_ok: bool | None = None
    failing_checks: list[str] = Field(default_factory=list)
    skipped_checks: list[str] = Field(default_factory=list)
    code_sandbox_effective_enabled: bool | None = None
    workbench_effective_enabled: bool | None = None
    app_data_dir: str | None = None
    runtime_root: str | None = None
    data_dir: str | None = None
    log_dir: str | None = None
    log_db_path: str | None = None
    packaged_shell_log_path: str | None = None
