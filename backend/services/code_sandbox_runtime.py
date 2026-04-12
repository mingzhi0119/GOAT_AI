"""SQLite persistence for durable code sandbox executions."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from backend.domain.resource_ownership import (
    PersistedResourceOwnership,
    ownership_from_fields,
)
from backend.services.sqlite_persistence_utils import raise_write_error

LogStreamName = Literal["stdout", "stderr"]


@dataclass(frozen=True, kw_only=True)
class CodeSandboxExecutionRecord:
    """Durable code sandbox execution record."""

    id: str
    status: str
    execution_mode: str
    runtime_preset: str
    network_policy: str
    timeout_sec: int
    code: str | None
    command: str | None
    stdin: str | None
    inline_files: list[dict[str, object]]
    created_at: str
    queued_at: str
    updated_at: str
    started_at: str | None = None
    finished_at: str | None = None
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    error_detail: str | None = None
    output_files: list[dict[str, object]] | None = None
    provider_name: str = ""
    last_log_seq: int = 0
    owner_id: str = ""
    tenant_id: str = "tenant:default"
    principal_id: str = ""
    auth_scopes: list[str] | None = None
    credential_id: str = ""
    auth_mode: str = ""

    @property
    def ownership(self) -> PersistedResourceOwnership:
        return ownership_from_fields(
            owner_id=self.owner_id,
            tenant_id=self.tenant_id,
            principal_id=self.principal_id,
        )


@dataclass(frozen=True, kw_only=True)
class CodeSandboxExecutionEventRecord:
    """Durable code sandbox execution event."""

    execution_id: str
    sequence: int
    event_type: str
    created_at: str
    status: str | None = None
    message: str | None = None
    metadata: dict[str, object] | None = None


@dataclass(frozen=True, kw_only=True)
class CodeSandboxLogChunkRecord:
    """One persisted stdout/stderr chunk for an execution."""

    execution_id: str
    sequence: int
    stream_name: LogStreamName
    created_at: str
    chunk_text: str


@dataclass(frozen=True, kw_only=True)
class CodeSandboxExecutionCreatePayload:
    """Initial persisted state for one accepted execution."""

    execution_id: str
    execution_mode: str
    runtime_preset: str
    network_policy: str
    timeout_sec: int
    code: str | None
    command: str | None
    stdin: str | None
    inline_files: list[dict[str, object]]
    created_at: str
    queued_at: str
    updated_at: str
    provider_name: str
    owner_id: str = ""
    tenant_id: str = "tenant:default"
    principal_id: str = ""
    auth_scopes: list[str] | None = None
    credential_id: str = ""
    auth_mode: str = ""
    status: str = "queued"

    @property
    def ownership(self) -> PersistedResourceOwnership:
        return ownership_from_fields(
            owner_id=self.owner_id,
            tenant_id=self.tenant_id,
            principal_id=self.principal_id,
        )


class CodeSandboxExecutionRepository(Protocol):
    """Persistence boundary for durable code sandbox execution records."""

    def create_execution(
        self, payload: CodeSandboxExecutionCreatePayload
    ) -> CodeSandboxExecutionRecord: ...

    def mark_execution_started(
        self,
        execution_id: str,
        *,
        updated_at: str,
        provider_name: str,
    ) -> CodeSandboxExecutionRecord | None: ...

    def mark_execution_completed(
        self,
        execution_id: str,
        *,
        updated_at: str,
        finished_at: str,
        exit_code: int,
        stdout: str,
        stderr: str,
        timed_out: bool,
        error_detail: str | None,
        output_files: list[dict[str, object]],
    ) -> None: ...

    def mark_execution_failed(
        self,
        execution_id: str,
        *,
        updated_at: str,
        finished_at: str,
        stdout: str,
        stderr: str,
        timed_out: bool,
        error_detail: str,
        output_files: list[dict[str, object]],
        exit_code: int | None = None,
    ) -> None: ...

    def mark_execution_denied(
        self,
        execution_id: str,
        *,
        updated_at: str,
        finished_at: str,
        error_detail: str,
    ) -> None: ...

    def mark_execution_cancelled(
        self,
        execution_id: str,
        *,
        updated_at: str,
        finished_at: str,
        error_detail: str,
    ) -> None: ...

    def get_execution(self, execution_id: str) -> CodeSandboxExecutionRecord | None: ...

    def list_execution_events(
        self, execution_id: str
    ) -> list[CodeSandboxExecutionEventRecord]: ...

    def append_execution_event(
        self,
        execution_id: str,
        *,
        event_type: str,
        created_at: str,
        status: str | None,
        message: str | None,
        metadata: dict[str, object] | None,
    ) -> None: ...

    def append_log_chunk(
        self,
        execution_id: str,
        *,
        created_at: str,
        stream_name: LogStreamName,
        chunk_text: str,
    ) -> int: ...

    def list_log_chunks(
        self, execution_id: str, *, after_sequence: int = 0
    ) -> list[CodeSandboxLogChunkRecord]: ...

    def list_execution_ids_by_status(self, *statuses: str) -> list[str]: ...


class SQLiteCodeSandboxExecutionRepository:
    """SQLite-backed persistence for code sandbox executions."""

    def __init__(self, db_path: Path) -> None:
        from backend.services.code_sandbox_execution_store import (
            SQLiteCodeSandboxExecutionStore,
        )
        from backend.services.code_sandbox_log_store import SQLiteCodeSandboxLogStore

        self._db_path = db_path
        self._execution_store = SQLiteCodeSandboxExecutionStore(db_path)
        self._log_store = SQLiteCodeSandboxLogStore(db_path)

    def create_execution(
        self, payload: CodeSandboxExecutionCreatePayload
    ) -> CodeSandboxExecutionRecord:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                self._execution_store.create_execution_in_transaction(conn, payload)
                conn.commit()
        except Exception as exc:
            raise_write_error("code_sandbox_execution_create", exc)
        return self._execution_store.get_execution(
            payload.execution_id
        ) or CodeSandboxExecutionRecord(
            id=payload.execution_id,
            status=payload.status,
            execution_mode=payload.execution_mode,
            runtime_preset=payload.runtime_preset,
            network_policy=payload.network_policy,
            timeout_sec=payload.timeout_sec,
            code=payload.code,
            command=payload.command,
            stdin=payload.stdin,
            inline_files=list(payload.inline_files),
            created_at=payload.created_at,
            queued_at=payload.queued_at,
            updated_at=payload.updated_at,
            provider_name=payload.provider_name,
            owner_id=payload.owner_id,
            tenant_id=payload.tenant_id,
            principal_id=payload.principal_id,
            auth_scopes=list(payload.auth_scopes or []),
            credential_id=payload.credential_id,
            auth_mode=payload.auth_mode,
        )

    def mark_execution_started(
        self,
        execution_id: str,
        *,
        updated_at: str,
        provider_name: str,
    ) -> CodeSandboxExecutionRecord | None:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                updated = self._execution_store.mark_execution_started_in_transaction(
                    conn,
                    execution_id,
                    updated_at=updated_at,
                    provider_name=provider_name,
                )
                if not updated:
                    conn.rollback()
                    return None
                conn.commit()
        except Exception as exc:
            raise_write_error("code_sandbox_execution_start", exc)
        return self._execution_store.get_execution(execution_id)

    def mark_execution_completed(
        self,
        execution_id: str,
        *,
        updated_at: str,
        finished_at: str,
        exit_code: int,
        stdout: str,
        stderr: str,
        timed_out: bool,
        error_detail: str | None,
        output_files: list[dict[str, object]],
    ) -> None:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                updated = self._execution_store.mark_execution_completed_in_transaction(
                    conn,
                    execution_id,
                    updated_at=updated_at,
                    finished_at=finished_at,
                    exit_code=exit_code,
                    stdout=stdout,
                    stderr=stderr,
                    timed_out=timed_out,
                    error_detail=error_detail,
                    output_files=output_files,
                )
                if not updated:
                    conn.rollback()
                    return
                conn.commit()
        except Exception as exc:
            raise_write_error("code_sandbox_execution_complete", exc)

    def mark_execution_failed(
        self,
        execution_id: str,
        *,
        updated_at: str,
        finished_at: str,
        stdout: str,
        stderr: str,
        timed_out: bool,
        error_detail: str,
        output_files: list[dict[str, object]],
        exit_code: int | None = None,
    ) -> None:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                updated = self._execution_store.mark_execution_failed_in_transaction(
                    conn,
                    execution_id,
                    updated_at=updated_at,
                    finished_at=finished_at,
                    stdout=stdout,
                    stderr=stderr,
                    timed_out=timed_out,
                    error_detail=error_detail,
                    output_files=output_files,
                    exit_code=exit_code,
                )
                if not updated:
                    conn.rollback()
                    return
                conn.commit()
        except Exception as exc:
            raise_write_error("code_sandbox_execution_fail", exc)

    def mark_execution_denied(
        self,
        execution_id: str,
        *,
        updated_at: str,
        finished_at: str,
        error_detail: str,
    ) -> None:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                updated = self._execution_store.mark_execution_denied_in_transaction(
                    conn,
                    execution_id,
                    updated_at=updated_at,
                    finished_at=finished_at,
                    error_detail=error_detail,
                )
                if not updated:
                    conn.rollback()
                    return
                conn.commit()
        except Exception as exc:
            raise_write_error("code_sandbox_execution_deny", exc)

    def mark_execution_cancelled(
        self,
        execution_id: str,
        *,
        updated_at: str,
        finished_at: str,
        error_detail: str,
    ) -> None:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                updated = self._execution_store.mark_execution_cancelled_in_transaction(
                    conn,
                    execution_id,
                    updated_at=updated_at,
                    finished_at=finished_at,
                    error_detail=error_detail,
                )
                if not updated:
                    conn.rollback()
                    return
                conn.commit()
        except Exception as exc:
            raise_write_error("code_sandbox_execution_cancel", exc)

    def get_execution(self, execution_id: str) -> CodeSandboxExecutionRecord | None:
        return self._execution_store.get_execution(execution_id)

    def list_execution_events(
        self, execution_id: str
    ) -> list[CodeSandboxExecutionEventRecord]:
        return self._execution_store.list_execution_events(execution_id)

    def append_execution_event(
        self,
        execution_id: str,
        *,
        event_type: str,
        created_at: str,
        status: str | None,
        message: str | None,
        metadata: dict[str, object] | None,
    ) -> None:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                self._execution_store.append_execution_event_in_transaction(
                    conn,
                    execution_id=execution_id,
                    event_type=event_type,
                    created_at=created_at,
                    status=status,
                    message=message,
                    metadata=metadata,
                )
                conn.commit()
        except Exception as exc:
            raise_write_error("code_sandbox_execution_event_append", exc)

    def append_log_chunk(
        self,
        execution_id: str,
        *,
        created_at: str,
        stream_name: LogStreamName,
        chunk_text: str,
    ) -> int:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                next_seq = self._log_store.append_log_chunk_in_transaction(
                    conn,
                    execution_id,
                    created_at=created_at,
                    stream_name=stream_name,
                    chunk_text=chunk_text,
                )
                conn.commit()
                return next_seq
        except Exception as exc:
            raise_write_error("code_sandbox_log_chunk_append", exc)

    def list_log_chunks(
        self, execution_id: str, *, after_sequence: int = 0
    ) -> list[CodeSandboxLogChunkRecord]:
        return self._log_store.list_log_chunks(
            execution_id, after_sequence=after_sequence
        )

    def list_execution_ids_by_status(self, *statuses: str) -> list[str]:
        return self._execution_store.list_execution_ids_by_status(*statuses)
