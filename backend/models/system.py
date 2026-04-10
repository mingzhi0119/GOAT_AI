"""Pydantic schemas for system telemetry endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


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


class RuntimeTargetResponse(BaseModel):
    """Resolved runtime target metadata used by deploy/ops tooling."""

    deploy_target: str
    current: RuntimeTargetItemResponse
    ordered_targets: list[RuntimeTargetItemResponse]


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
    project_memory: RuntimeFeaturePayload
    connectors: RuntimeFeaturePayload


class SystemFeaturesResponse(BaseModel):
    """Public feature flags derived from config + host probes."""

    code_sandbox: CodeSandboxFeaturePayload
    workbench: WorkbenchFeaturePayload
