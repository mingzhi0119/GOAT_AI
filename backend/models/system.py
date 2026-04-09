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

    **Policy / AuthZ** (per-user, per-role) is separate: use ``policy_allowed`` when implemented;
    until then it stays ``null``. Do not confuse with Docker/runtime probes below.
    """

    policy_allowed: bool | None = Field(
        default=None,
        description="Reserved for authorization; null until AuthZ lands.",
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


class SystemFeaturesResponse(BaseModel):
    """Public feature flags derived from config + host probes."""

    code_sandbox: CodeSandboxFeaturePayload
