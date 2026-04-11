"""Execution orchestration for durable code sandbox runs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from backend.services.code_sandbox_provider import (
    SandboxProvider,
    SandboxProviderLogChunk,
    SandboxProviderRequest,
    SandboxProviderResult,
)
from backend.services.code_sandbox_runtime import CodeSandboxExecutionRepository
from backend.types import Settings


def _is_terminal_status(status: str) -> bool:
    return status in {"completed", "failed", "denied"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class _BoundedTextAccumulator:
    max_bytes: int
    _text_parts: list[str]
    _bytes_used: int = 0
    _truncated: bool = False

    def __init__(self, *, max_bytes: int) -> None:
        self.max_bytes = max_bytes
        self._text_parts = []

    def append(self, text: str) -> str | None:
        if not text or self.max_bytes <= 0:
            return None
        if self._truncated:
            return None
        encoded = text.encode("utf-8")
        remaining = self.max_bytes - self._bytes_used
        if remaining <= 0:
            self._truncated = True
            return None
        if len(encoded) <= remaining:
            self._text_parts.append(text)
            self._bytes_used += len(encoded)
            return text
        clipped = encoded[:remaining].decode("utf-8", errors="ignore")
        marker = "\n[output truncated]"
        out = f"{clipped}{marker}"
        self._text_parts.append(out)
        self._bytes_used = self.max_bytes
        self._truncated = True
        return out

    @property
    def text(self) -> str:
        return "".join(self._text_parts)


def _provider_request_from_execution(
    execution_id: str,
    *,
    repository: CodeSandboxExecutionRepository,
) -> SandboxProviderRequest | None:
    record = repository.get_execution(execution_id)
    if record is None:
        return None
    return SandboxProviderRequest(
        execution_id=record.id,
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
        timeout_sec=(
            0
        ),  # placeholder replaced by application-managed normalization at create time
        network_policy=record.network_policy,
    )


def build_provider_request_for_execution(
    execution_id: str,
    *,
    repository: CodeSandboxExecutionRepository,
) -> SandboxProviderRequest | None:
    request = _provider_request_from_execution(
        execution_id,
        repository=repository,
    )
    if request is None:
        return None
    record = repository.get_execution(execution_id)
    if record is None:
        return None
    return SandboxProviderRequest(
        execution_id=request.execution_id,
        runtime_preset=request.runtime_preset,
        code=request.code,
        command=request.command,
        stdin=request.stdin,
        inline_files=request.inline_files,
        timeout_sec=record.timeout_sec,
        network_policy=request.network_policy,
    )


def execute_code_sandbox_execution(
    *,
    execution_id: str,
    repository: CodeSandboxExecutionRepository,
    provider: SandboxProvider,
    settings: Settings,
    raise_errors: bool = False,
) -> None:
    record = repository.get_execution(execution_id)
    if record is None or _is_terminal_status(record.status):
        return

    started = repository.mark_execution_started(
        execution_id,
        updated_at=_utc_now(),
        provider_name=provider.provider_name,
    )
    if started is None:
        return

    provider_request = build_provider_request_for_execution(
        execution_id,
        repository=repository,
    )
    if provider_request is None:
        return

    stdout_acc = _BoundedTextAccumulator(
        max_bytes=settings.code_sandbox_max_output_bytes
    )
    stderr_acc = _BoundedTextAccumulator(
        max_bytes=settings.code_sandbox_max_output_bytes
    )
    terminal: SandboxProviderResult | None = None

    try:
        for item in provider.run_stream(provider_request):
            if isinstance(item, SandboxProviderLogChunk):
                accumulator = stdout_acc if item.stream_name == "stdout" else stderr_acc
                clipped = accumulator.append(item.text)
                if clipped:
                    repository.append_log_chunk(
                        execution_id,
                        created_at=item.created_at,
                        stream_name=item.stream_name,
                        chunk_text=clipped,
                    )
                continue
            terminal = item
    except Exception:
        failed_at = _utc_now()
        repository.mark_execution_failed(
            execution_id,
            updated_at=failed_at,
            finished_at=failed_at,
            stdout=stdout_acc.text,
            stderr=stderr_acc.text,
            timed_out=False,
            error_detail="Sandbox runtime failed before completion.",
            output_files=[],
            exit_code=None,
        )
        if raise_errors:
            raise
        return

    if terminal is None:
        repository.mark_execution_failed(
            execution_id,
            updated_at=_utc_now(),
            finished_at=_utc_now(),
            stdout=stdout_acc.text,
            stderr=stderr_acc.text,
            timed_out=False,
            error_detail="Sandbox provider returned no terminal result.",
            output_files=[],
            exit_code=None,
        )
        return

    if terminal.stdout:
        clipped = stdout_acc.append(terminal.stdout)
        if clipped:
            repository.append_log_chunk(
                execution_id,
                created_at=_utc_now(),
                stream_name="stdout",
                chunk_text=clipped,
            )
    if terminal.stderr:
        clipped = stderr_acc.append(terminal.stderr)
        if clipped:
            repository.append_log_chunk(
                execution_id,
                created_at=_utc_now(),
                stream_name="stderr",
                chunk_text=clipped,
            )

    finished_at = _utc_now()
    if (
        terminal.timed_out
        or terminal.exit_code not in (0, None)
        or terminal.error_detail
    ):
        repository.mark_execution_failed(
            execution_id,
            updated_at=finished_at,
            finished_at=finished_at,
            stdout=stdout_acc.text,
            stderr=stderr_acc.text,
            timed_out=terminal.timed_out,
            error_detail=terminal.error_detail or "Execution failed.",
            output_files=[dict(item) for item in terminal.output_files],
            exit_code=terminal.exit_code,
        )
        return

    repository.mark_execution_completed(
        execution_id,
        updated_at=finished_at,
        finished_at=finished_at,
        exit_code=terminal.exit_code or 0,
        stdout=stdout_acc.text,
        stderr=stderr_acc.text,
        timed_out=False,
        error_detail=None,
        output_files=[dict(item) for item in terminal.output_files],
    )


def recover_queued_code_sandbox_executions(
    *,
    repository: CodeSandboxExecutionRepository,
    provider: SandboxProvider,
    settings: Settings,
) -> list[str]:
    """Best-effort in-process recovery for executions left queued across restarts."""
    recovered: list[str] = []
    for execution_id in repository.list_execution_ids_by_status("queued"):
        execute_code_sandbox_execution(
            execution_id=execution_id,
            repository=repository,
            provider=provider,
            settings=settings,
            raise_errors=False,
        )
        recovered.append(execution_id)
    return recovered
