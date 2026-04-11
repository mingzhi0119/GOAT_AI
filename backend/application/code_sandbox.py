"""Code sandbox application use cases."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import PurePosixPath
from uuid import uuid4

from backend.application.exceptions import (
    CodeSandboxExecutionNotFoundError,
    CodeSandboxValidationError,
)
from backend.application.ports import (
    CodeSandboxExecutionRepository,
    SandboxProvider,
    Settings,
)
from backend.domain.authz_types import AuthorizationContext
from backend.models.code_sandbox import (
    CodeSandboxExecRequest,
    CodeSandboxExecutionEventPayload,
    CodeSandboxExecutionEventsResponse,
    CodeSandboxExecutionResponse,
    CodeSandboxOutputFilePayload,
)
from backend.services.authorizer import authorize_code_sandbox_execution_read
from backend.services.code_sandbox_provider import SandboxProviderRequest
from backend.services.code_sandbox_runtime import (
    CodeSandboxExecutionCreatePayload,
    CodeSandboxExecutionEventRecord,
    CodeSandboxExecutionRecord,
)
from backend.services.feature_gate_service import require_code_sandbox_enabled


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_code_sandbox_enabled(
    settings: Settings,
    auth_context: AuthorizationContext,
) -> None:
    require_code_sandbox_enabled(settings, auth_context)


def _validate_relative_workspace_path(raw: str) -> str:
    path = PurePosixPath(raw.strip())
    if not raw.strip():
        raise CodeSandboxValidationError("Inline file paths must not be empty.")
    if path.is_absolute():
        raise CodeSandboxValidationError(
            "Inline files must use relative workspace paths."
        )
    if any(part in {"..", "."} for part in path.parts):
        raise CodeSandboxValidationError(
            "Inline files must stay within the sandbox workspace."
        )
    return path.as_posix()


def _normalize_request(
    *,
    request: CodeSandboxExecRequest,
    settings: Settings,
    execution_id: str,
) -> SandboxProviderRequest:
    code = request.code.strip() if request.code is not None else None
    command = request.command.strip() if request.command is not None else None
    stdin = request.stdin if request.stdin is not None else None
    if (
        stdin is not None
        and len(stdin.encode("utf-8")) > settings.code_sandbox_max_stdin_bytes
    ):
        raise CodeSandboxValidationError("stdin exceeds the configured size limit.")
    if (
        code is not None
        and len(code.encode("utf-8")) > settings.code_sandbox_max_code_bytes
    ):
        raise CodeSandboxValidationError("Code exceeds the configured size limit.")
    if (
        command is not None
        and len(command.encode("utf-8")) > settings.code_sandbox_max_command_bytes
    ):
        raise CodeSandboxValidationError("Command exceeds the configured size limit.")
    if not code and not command:
        raise CodeSandboxValidationError("Provide either `code` or `command`.")
    if len(request.files) > settings.code_sandbox_max_inline_files:
        raise CodeSandboxValidationError("Too many inline files were provided.")
    if request.network_policy not in (None, "disabled"):
        raise CodeSandboxValidationError(
            "Phase 18 only supports `network_policy = disabled`."
        )
    timeout_sec = request.timeout_sec or settings.code_sandbox_default_timeout_sec
    if timeout_sec < 1 or timeout_sec > settings.code_sandbox_max_timeout_sec:
        raise CodeSandboxValidationError(
            "timeout_sec exceeds the configured execution limit."
        )
    inline_files: list[dict[str, str]] = []
    for item in request.files:
        content_bytes = item.content.encode("utf-8")
        if len(content_bytes) > settings.code_sandbox_max_inline_file_bytes:
            raise CodeSandboxValidationError(
                f"Inline file `{item.filename}` exceeds the configured size limit."
            )
        inline_files.append(
            {
                "filename": _validate_relative_workspace_path(item.filename),
                "content": item.content,
            }
        )
    return SandboxProviderRequest(
        execution_id=execution_id,
        runtime_preset=request.runtime_preset,
        code=code,
        command=command,
        stdin=stdin,
        inline_files=inline_files,
        timeout_sec=timeout_sec,
        network_policy="disabled",
    )


def _to_execution_response(
    record: CodeSandboxExecutionRecord,
) -> CodeSandboxExecutionResponse:
    return CodeSandboxExecutionResponse(
        execution_id=record.id,
        status=record.status,
        runtime_preset=record.runtime_preset,
        network_policy=record.network_policy,
        created_at=record.created_at,
        updated_at=record.updated_at,
        exit_code=record.exit_code,
        stdout=record.stdout,
        stderr=record.stderr,
        timed_out=record.timed_out,
        error_detail=record.error_detail,
        output_files=[
            CodeSandboxOutputFilePayload.model_validate(item)
            for item in (record.output_files or [])
        ],
    )


def _to_event_payload(
    event: CodeSandboxExecutionEventRecord,
) -> CodeSandboxExecutionEventPayload:
    return CodeSandboxExecutionEventPayload(
        sequence=event.sequence,
        event_type=event.event_type,
        created_at=event.created_at,
        status=event.status,
        message=event.message,
        metadata=dict(event.metadata or {}),
    )


def execute_code_sandbox_request(
    *,
    request: CodeSandboxExecRequest,
    repository: CodeSandboxExecutionRepository,
    provider: SandboxProvider,
    settings: Settings,
    auth_context: AuthorizationContext,
) -> CodeSandboxExecutionResponse:
    """Validate, persist, execute, and return one short synchronous sandbox run."""
    ensure_code_sandbox_enabled(settings, auth_context)
    execution_id = f"cs-{uuid4().hex}"
    now = _utc_now()
    provider_request = _normalize_request(
        request=request,
        settings=settings,
        execution_id=execution_id,
    )
    repository.create_execution(
        CodeSandboxExecutionCreatePayload(
            execution_id=execution_id,
            runtime_preset=provider_request.runtime_preset,
            network_policy=provider_request.network_policy,
            code=provider_request.code,
            command=provider_request.command,
            stdin=provider_request.stdin,
            inline_files=list(provider_request.inline_files),
            created_at=now,
            updated_at=now,
            owner_id=auth_context.legacy_owner_id,
            tenant_id=auth_context.tenant_id.value,
            principal_id=auth_context.principal_id.value,
            auth_scopes=sorted(auth_context.scopes),
            credential_id=auth_context.credential_id,
            auth_mode=auth_context.auth_mode,
        )
    )
    repository.mark_execution_started(
        execution_id,
        updated_at=now,
        provider_name=provider.provider_name,
    )
    result = provider.run(provider_request)
    finished_at = _utc_now()
    output_files = [dict(item) for item in result.output_files]
    if result.timed_out or result.exit_code not in (0, None):
        repository.mark_execution_failed(
            execution_id,
            updated_at=finished_at,
            finished_at=finished_at,
            stdout=result.stdout,
            stderr=result.stderr,
            timed_out=result.timed_out,
            error_detail=result.error_detail or "Execution failed.",
            output_files=output_files,
            exit_code=result.exit_code,
        )
    elif result.error_detail:
        repository.mark_execution_failed(
            execution_id,
            updated_at=finished_at,
            finished_at=finished_at,
            stdout=result.stdout,
            stderr=result.stderr,
            timed_out=False,
            error_detail=result.error_detail,
            output_files=output_files,
            exit_code=result.exit_code,
        )
    else:
        repository.mark_execution_completed(
            execution_id,
            updated_at=finished_at,
            finished_at=finished_at,
            exit_code=result.exit_code or 0,
            stdout=result.stdout,
            stderr=result.stderr,
            timed_out=False,
            error_detail=None,
            output_files=output_files,
        )
    record = repository.get_execution(execution_id)
    if record is None:
        raise RuntimeError("Code sandbox execution disappeared after completion.")
    return _to_execution_response(record)


def get_code_sandbox_execution(
    *,
    execution_id: str,
    repository: CodeSandboxExecutionRepository,
    settings: Settings,
    auth_context: AuthorizationContext,
) -> CodeSandboxExecutionResponse:
    """Return one visible durable code sandbox execution."""
    ensure_code_sandbox_enabled(settings, auth_context)
    record = repository.get_execution(execution_id)
    if record is None:
        raise CodeSandboxExecutionNotFoundError("Code sandbox execution not found")
    decision = authorize_code_sandbox_execution_read(
        ctx=auth_context,
        execution=record,
        require_owner_header=settings.require_session_owner,
    )
    if not decision.allowed:
        raise CodeSandboxExecutionNotFoundError("Code sandbox execution not found")
    return _to_execution_response(record)


def get_code_sandbox_execution_events(
    *,
    execution_id: str,
    repository: CodeSandboxExecutionRepository,
    settings: Settings,
    auth_context: AuthorizationContext,
) -> CodeSandboxExecutionEventsResponse:
    """Return the durable event timeline for one visible sandbox execution."""
    ensure_code_sandbox_enabled(settings, auth_context)
    record = repository.get_execution(execution_id)
    if record is None:
        raise CodeSandboxExecutionNotFoundError("Code sandbox execution not found")
    decision = authorize_code_sandbox_execution_read(
        ctx=auth_context,
        execution=record,
        require_owner_header=settings.require_session_owner,
    )
    if not decision.allowed:
        raise CodeSandboxExecutionNotFoundError("Code sandbox execution not found")
    return CodeSandboxExecutionEventsResponse(
        execution_id=record.id,
        events=[
            _to_event_payload(event)
            for event in repository.list_execution_events(record.id)
        ],
    )
