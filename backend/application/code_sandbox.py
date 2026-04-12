"""Code sandbox application use cases."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Generator
from uuid import uuid4

from fastapi.responses import StreamingResponse

from backend.application.exceptions import (
    CodeSandboxExecutionConflictError,
    CodeSandboxExecutionNotFoundError,
    CodeSandboxValidationError,
)
from backend.application.ports import (
    CodeSandboxExecutionDispatcher,
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
from backend.services.code_sandbox_execution_service import (
    execute_code_sandbox_execution,
)
from backend.services.code_sandbox_provider import SandboxProviderRequest
from backend.services.code_sandbox_provider import (
    sandbox_provider_enforces_network_policy,
    sandbox_provider_isolation_level,
)
from backend.services.code_sandbox_runtime import (
    CodeSandboxExecutionCreatePayload,
    CodeSandboxExecutionEventRecord,
    CodeSandboxLogChunkRecord,
    CodeSandboxExecutionRecord,
)
from backend.services.feature_gate_service import require_code_sandbox_enabled
from backend.services.sse import sse_done_event, sse_event

_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True, kw_only=True)
class _NormalizedSandboxRequest:
    execution_mode: str
    provider_request: SandboxProviderRequest


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
) -> _NormalizedSandboxRequest:
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
            "Phase 18A only supports `network_policy = disabled`."
        )
    if request.execution_mode not in {"sync", "async"}:
        raise CodeSandboxValidationError("Unsupported execution mode.")
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
    return _NormalizedSandboxRequest(
        execution_mode=request.execution_mode,
        provider_request=SandboxProviderRequest(
            execution_id=execution_id,
            runtime_preset=request.runtime_preset,
            code=code,
            command=command,
            stdin=stdin,
            inline_files=inline_files,
            timeout_sec=timeout_sec,
            network_policy="disabled",
        ),
    )


def _to_execution_response(
    record: CodeSandboxExecutionRecord,
) -> CodeSandboxExecutionResponse:
    provider_name = record.provider_name or "docker"
    return CodeSandboxExecutionResponse(
        execution_id=record.id,
        status=record.status,
        execution_mode=record.execution_mode,
        runtime_preset=record.runtime_preset,
        network_policy=record.network_policy,
        created_at=record.created_at,
        updated_at=record.updated_at,
        started_at=record.started_at,
        finished_at=record.finished_at,
        provider_name=provider_name,
        isolation_level=sandbox_provider_isolation_level(provider_name),
        network_policy_enforced=sandbox_provider_enforces_network_policy(provider_name),
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


def _build_create_payload(
    *,
    execution_id: str,
    execution_mode: str,
    provider_request: SandboxProviderRequest,
    created_at: str,
    provider_name: str,
    owner_id: str,
    tenant_id: str,
    principal_id: str,
    auth_scopes: list[str] | None,
    credential_id: str,
    auth_mode: str,
) -> CodeSandboxExecutionCreatePayload:
    return CodeSandboxExecutionCreatePayload(
        execution_id=execution_id,
        execution_mode=execution_mode,
        runtime_preset=provider_request.runtime_preset,
        network_policy=provider_request.network_policy,
        timeout_sec=provider_request.timeout_sec,
        code=provider_request.code,
        command=provider_request.command,
        stdin=provider_request.stdin,
        inline_files=list(provider_request.inline_files),
        created_at=created_at,
        queued_at=created_at,
        updated_at=created_at,
        provider_name=provider_name,
        owner_id=owner_id,
        tenant_id=tenant_id,
        principal_id=principal_id,
        auth_scopes=list(auth_scopes or []),
        credential_id=credential_id,
        auth_mode=auth_mode,
    )


def _load_visible_execution(
    *,
    execution_id: str,
    repository: CodeSandboxExecutionRepository,
    settings: Settings,
    auth_context: AuthorizationContext,
) -> CodeSandboxExecutionRecord:
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
    return record


def execute_code_sandbox_request(
    *,
    request: CodeSandboxExecRequest,
    repository: CodeSandboxExecutionRepository,
    provider: SandboxProvider,
    dispatcher: CodeSandboxExecutionDispatcher,
    settings: Settings,
    auth_context: AuthorizationContext,
) -> CodeSandboxExecutionResponse:
    """Validate, persist, execute, and return one sandbox run."""
    ensure_code_sandbox_enabled(settings, auth_context)
    execution_id = f"cs-{uuid4().hex}"
    normalized = _normalize_request(
        request=request,
        settings=settings,
        execution_id=execution_id,
    )
    now = _utc_now()
    repository.create_execution(
        _build_create_payload(
            execution_id=execution_id,
            execution_mode=normalized.execution_mode,
            provider_request=normalized.provider_request,
            created_at=now,
            provider_name=provider.provider_name,
            owner_id=auth_context.legacy_owner_id,
            tenant_id=auth_context.tenant_id.value,
            principal_id=auth_context.principal_id.value,
            auth_scopes=sorted(auth_context.scopes),
            credential_id=auth_context.credential_id,
            auth_mode=auth_context.auth_mode,
        )
    )
    if normalized.execution_mode == "async":
        dispatcher.dispatch_execution(execution_id=execution_id)
    else:
        execute_code_sandbox_execution(
            execution_id=execution_id,
            repository=repository,
            provider=provider,
            settings=settings,
            raise_errors=True,
        )
    record = repository.get_execution(execution_id)
    if record is None:
        raise RuntimeError("Code sandbox execution disappeared after submission.")
    return _to_execution_response(record)


def get_code_sandbox_execution(
    *,
    execution_id: str,
    repository: CodeSandboxExecutionRepository,
    settings: Settings,
    auth_context: AuthorizationContext,
) -> CodeSandboxExecutionResponse:
    """Return one visible durable code sandbox execution."""
    return _to_execution_response(
        _load_visible_execution(
            execution_id=execution_id,
            repository=repository,
            settings=settings,
            auth_context=auth_context,
        )
    )


def cancel_code_sandbox_execution(
    *,
    execution_id: str,
    repository: CodeSandboxExecutionRepository,
    settings: Settings,
    auth_context: AuthorizationContext,
) -> CodeSandboxExecutionResponse:
    """Cancel one visible queued code sandbox execution."""
    ensure_code_sandbox_enabled(settings, auth_context)
    record = _load_visible_execution(
        execution_id=execution_id,
        repository=repository,
        settings=settings,
        auth_context=auth_context,
    )
    if record.status != "queued":
        raise CodeSandboxExecutionConflictError(
            "Only queued code sandbox executions can be cancelled."
        )
    now = _utc_now()
    repository.mark_execution_cancelled(
        execution_id,
        updated_at=now,
        finished_at=now,
        error_detail="Execution cancelled before start.",
    )
    updated = repository.get_execution(execution_id)
    if updated is None:
        raise RuntimeError("Code sandbox execution disappeared after cancellation.")
    return _to_execution_response(updated)


def retry_code_sandbox_execution(
    *,
    execution_id: str,
    repository: CodeSandboxExecutionRepository,
    provider: SandboxProvider,
    dispatcher: CodeSandboxExecutionDispatcher,
    settings: Settings,
    auth_context: AuthorizationContext,
) -> CodeSandboxExecutionResponse:
    """Re-submit one visible terminal code sandbox execution as a new execution."""
    ensure_code_sandbox_enabled(settings, auth_context)
    record = _load_visible_execution(
        execution_id=execution_id,
        repository=repository,
        settings=settings,
        auth_context=auth_context,
    )
    if record.status not in {"completed", "failed", "denied", "cancelled"}:
        raise CodeSandboxExecutionConflictError(
            "Only terminal code sandbox executions can be retried."
        )

    retry_execution_id = f"cs-{uuid4().hex}"
    now = _utc_now()
    repository.create_execution(
        _build_create_payload(
            execution_id=retry_execution_id,
            execution_mode=record.execution_mode,
            provider_request=SandboxProviderRequest(
                execution_id=retry_execution_id,
                runtime_preset=record.runtime_preset,
                code=record.code,
                command=record.command,
                stdin=record.stdin,
                inline_files=[
                    {
                        "filename": str(item.get("filename", "")),
                        "content": str(item.get("content", "")),
                    }
                    for item in record.inline_files
                ],
                timeout_sec=record.timeout_sec,
                network_policy=record.network_policy,
            ),
            created_at=now,
            provider_name=provider.provider_name,
            owner_id=record.owner_id,
            tenant_id=record.tenant_id,
            principal_id=record.principal_id,
            auth_scopes=record.auth_scopes,
            credential_id=record.credential_id,
            auth_mode=record.auth_mode,
        )
    )
    repository.append_execution_event(
        execution_id,
        event_type="execution.retry_requested",
        created_at=now,
        status=record.status,
        message="Retry requested.",
        metadata={"retry_execution_id": retry_execution_id},
    )
    repository.append_execution_event(
        retry_execution_id,
        event_type="execution.retry_created",
        created_at=now,
        status="queued",
        message="Execution created from retry.",
        metadata={"source_execution_id": execution_id},
    )

    if record.execution_mode == "async":
        dispatcher.dispatch_execution(execution_id=retry_execution_id)
    else:
        execute_code_sandbox_execution(
            execution_id=retry_execution_id,
            repository=repository,
            provider=provider,
            settings=settings,
            raise_errors=True,
        )
    retry_record = repository.get_execution(retry_execution_id)
    if retry_record is None:
        raise RuntimeError("Code sandbox retry disappeared after submission.")
    return _to_execution_response(retry_record)


def get_code_sandbox_execution_events(
    *,
    execution_id: str,
    repository: CodeSandboxExecutionRepository,
    settings: Settings,
    auth_context: AuthorizationContext,
) -> CodeSandboxExecutionEventsResponse:
    """Return the durable event timeline for one visible execution."""
    record = _load_visible_execution(
        execution_id=execution_id,
        repository=repository,
        settings=settings,
        auth_context=auth_context,
    )
    return CodeSandboxExecutionEventsResponse(
        execution_id=record.id,
        events=[
            _to_event_payload(event)
            for event in repository.list_execution_events(execution_id)
        ],
    )


def stream_code_sandbox_execution_logs(
    *,
    execution_id: str,
    after_sequence: int,
    repository: CodeSandboxExecutionRepository,
    settings: Settings,
    auth_context: AuthorizationContext,
) -> StreamingResponse:
    """Return an SSE log stream for one visible durable execution."""
    _load_visible_execution(
        execution_id=execution_id,
        repository=repository,
        settings=settings,
        auth_context=auth_context,
    )

    def generate() -> Generator[str, None, None]:
        last_seq = max(after_sequence, 0)
        last_status: str | None = None
        while True:
            record = _load_visible_execution(
                execution_id=execution_id,
                repository=repository,
                settings=settings,
                auth_context=auth_context,
            )
            if record.status != last_status:
                last_status = record.status
                yield sse_event(
                    {
                        "type": "status",
                        "execution_id": record.id,
                        "status": record.status,
                        "provider_name": record.provider_name,
                        "updated_at": record.updated_at,
                        "timed_out": record.timed_out,
                    }
                )

            chunks = repository.list_log_chunks(
                execution_id,
                after_sequence=last_seq,
            )
            for chunk in chunks:
                last_seq = max(last_seq, chunk.sequence)
                yield _log_chunk_sse(chunk)

            if record.status in {"completed", "failed", "denied", "cancelled"}:
                yield sse_done_event()
                return

            time.sleep(0.2)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


def _log_chunk_sse(chunk: CodeSandboxLogChunkRecord) -> str:
    return sse_event(
        {
            "type": chunk.stream_name,
            "execution_id": chunk.execution_id,
            "sequence": chunk.sequence,
            "created_at": chunk.created_at,
            "chunk": chunk.chunk_text,
        }
    )
