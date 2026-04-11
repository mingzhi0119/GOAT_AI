"""Pydantic models for code sandbox execution."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


CodeSandboxStatus = Literal["queued", "running", "completed", "failed", "denied"]
CodeSandboxNetworkPolicy = Literal["disabled", "allowlist", "enabled"]
CodeSandboxRuntimePreset = Literal["shell"]


class CodeSandboxInlineFile(BaseModel):
    """One inline text file seeded into the ephemeral sandbox workspace."""

    filename: str = Field(
        ..., description="Relative workspace path for the seeded file."
    )
    content: str = Field(
        ..., description="UTF-8 text content written into the workspace."
    )


class CodeSandboxExecRequest(BaseModel):
    """Request body for one short synchronous sandbox execution."""

    runtime_preset: CodeSandboxRuntimePreset = Field(
        default="shell",
        description="Execution preset. Phase 18 supports a shell workspace only.",
    )
    code: str | None = Field(
        default=None,
        description="Shell script source. When command is omitted, the server executes this script.",
    )
    command: str | None = Field(
        default=None,
        description="Optional shell command executed inside the workspace.",
    )
    stdin: str | None = Field(
        default=None,
        description="Optional UTF-8 stdin content redirected into the entry command.",
    )
    timeout_sec: int | None = Field(
        default=None,
        description="Optional execution timeout override, capped by server policy.",
    )
    network_policy: CodeSandboxNetworkPolicy | None = Field(
        default=None,
        description="Reserved for future policies. Phase 18 only allows `disabled`.",
    )
    files: list[CodeSandboxInlineFile] = Field(
        default_factory=list,
        description="Optional inline text files seeded into the temporary workspace.",
    )


class CodeSandboxOutputFilePayload(BaseModel):
    """Metadata for one output file created under the sandbox outputs directory."""

    path: str = Field(
        ..., description="Relative path under `outputs/` in the workspace."
    )
    byte_size: int = Field(..., description="Output file size in bytes.")


class CodeSandboxExecutionResponse(BaseModel):
    """Synchronous result body and durable read model for one execution."""

    execution_id: str
    status: CodeSandboxStatus
    runtime_preset: CodeSandboxRuntimePreset
    network_policy: CodeSandboxNetworkPolicy
    created_at: str
    updated_at: str
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    error_detail: str | None = None
    output_files: list[CodeSandboxOutputFilePayload] = Field(default_factory=list)


class CodeSandboxExecutionEventPayload(BaseModel):
    """Durable sandbox execution timeline event."""

    sequence: int
    event_type: str
    created_at: str
    status: CodeSandboxStatus | None = None
    message: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class CodeSandboxExecutionEventsResponse(BaseModel):
    """Durable sandbox execution timeline response."""

    execution_id: str
    events: list[CodeSandboxExecutionEventPayload]
