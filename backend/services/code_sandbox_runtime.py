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
from backend.services.exceptions import PersistenceReadError, PersistenceWriteError
from backend.services.postgres_runtime_support import (
    lock_parent_row,
    next_scoped_sequence,
    postgres_connect,
)
from backend.services.sqlite_persistence_utils import (
    decode_files,
    decode_object,
    decode_string_list,
    encode_json,
    raise_write_error,
)

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
        output_files: list[dict[str, object]] | None = None,
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
        output_files: list[dict[str, object]] | None = None,
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
                    output_files=output_files,
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


class PostgresCodeSandboxExecutionRepository:
    """Postgres-backed persistence for code sandbox executions."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def create_execution(
        self, payload: CodeSandboxExecutionCreatePayload
    ) -> CodeSandboxExecutionRecord:
        try:
            with postgres_connect(self._dsn) as conn:
                with conn.transaction():
                    conn.execute(
                        """
                        INSERT INTO code_sandbox_executions (
                            id,
                            status,
                            execution_mode,
                            runtime_preset,
                            network_policy,
                            timeout_sec,
                            code,
                            command,
                            stdin_text,
                            inline_files_json,
                            created_at,
                            queued_at,
                            updated_at,
                            provider_name,
                            owner_id,
                            tenant_id,
                            principal_id,
                            auth_scopes_json,
                            credential_id,
                            auth_mode
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            payload.execution_id,
                            payload.status,
                            payload.execution_mode,
                            payload.runtime_preset,
                            payload.network_policy,
                            payload.timeout_sec,
                            payload.code,
                            payload.command,
                            payload.stdin,
                            encode_json(payload.inline_files),
                            payload.created_at,
                            payload.queued_at,
                            payload.updated_at,
                            payload.provider_name,
                            payload.owner_id,
                            payload.tenant_id,
                            payload.principal_id,
                            encode_json(payload.auth_scopes or []),
                            payload.credential_id,
                            payload.auth_mode,
                        ),
                    )
                    self._append_execution_event_in_transaction(
                        conn,
                        execution_id=payload.execution_id,
                        event_type="execution.queued",
                        created_at=payload.queued_at,
                        status=payload.status,
                        message="Execution accepted.",
                        metadata={
                            "execution_mode": payload.execution_mode,
                            "network_policy": payload.network_policy,
                            "runtime_preset": payload.runtime_preset,
                        },
                    )
        except Exception as exc:
            raise PersistenceWriteError(
                "Failed to code sandbox execution create."
            ) from exc
        return self.get_execution(payload.execution_id) or CodeSandboxExecutionRecord(
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
            with postgres_connect(self._dsn) as conn:
                with conn.transaction():
                    lock_parent_row(
                        conn,
                        table_name="code_sandbox_executions",
                        key_column="id",
                        key_value=execution_id,
                    )
                    cursor = conn.execute(
                        """
                        UPDATE code_sandbox_executions
                        SET status = 'running',
                            updated_at = %s,
                            started_at = COALESCE(started_at, %s),
                            provider_name = %s
                        WHERE id = %s AND status = 'queued'
                        """,
                        (updated_at, updated_at, provider_name, execution_id),
                    )
                    if cursor.rowcount == 0:
                        return None
                    self._append_execution_event_in_transaction(
                        conn,
                        execution_id=execution_id,
                        event_type="execution.started",
                        created_at=updated_at,
                        status="running",
                        message="Execution started.",
                        metadata={"provider_name": provider_name},
                    )
        except Exception as exc:
            raise PersistenceWriteError(
                "Failed to code sandbox execution start."
            ) from exc
        return self.get_execution(execution_id)

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
            with postgres_connect(self._dsn) as conn:
                with conn.transaction():
                    lock_parent_row(
                        conn,
                        table_name="code_sandbox_executions",
                        key_column="id",
                        key_value=execution_id,
                    )
                    cursor = conn.execute(
                        """
                        UPDATE code_sandbox_executions
                        SET status = 'completed',
                            updated_at = %s,
                            finished_at = %s,
                            exit_code = %s,
                            stdout = %s,
                            stderr = %s,
                            timed_out = %s,
                            error_detail = %s,
                            output_files_json = %s
                        WHERE id = %s AND status IN ('queued', 'running')
                        """,
                        (
                            updated_at,
                            finished_at,
                            exit_code,
                            stdout,
                            stderr,
                            int(timed_out),
                            error_detail,
                            encode_json(output_files),
                            execution_id,
                        ),
                    )
                    if cursor.rowcount == 0:
                        return
                    self._append_execution_event_in_transaction(
                        conn,
                        execution_id=execution_id,
                        event_type="execution.completed",
                        created_at=finished_at,
                        status="completed",
                        message="Execution completed.",
                        metadata={
                            "exit_code": exit_code,
                            "timed_out": timed_out,
                            "output_file_count": len(output_files),
                        },
                    )
        except Exception as exc:
            raise PersistenceWriteError(
                "Failed to code sandbox execution complete."
            ) from exc

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
            with postgres_connect(self._dsn) as conn:
                with conn.transaction():
                    lock_parent_row(
                        conn,
                        table_name="code_sandbox_executions",
                        key_column="id",
                        key_value=execution_id,
                    )
                    cursor = conn.execute(
                        """
                        UPDATE code_sandbox_executions
                        SET status = 'failed',
                            updated_at = %s,
                            finished_at = %s,
                            exit_code = %s,
                            stdout = %s,
                            stderr = %s,
                            timed_out = %s,
                            error_detail = %s,
                            output_files_json = %s
                        WHERE id = %s AND status IN ('queued', 'running')
                        """,
                        (
                            updated_at,
                            finished_at,
                            exit_code,
                            stdout,
                            stderr,
                            int(timed_out),
                            error_detail,
                            encode_json(output_files),
                            execution_id,
                        ),
                    )
                    if cursor.rowcount == 0:
                        return
                    self._append_execution_event_in_transaction(
                        conn,
                        execution_id=execution_id,
                        event_type="execution.failed",
                        created_at=finished_at,
                        status="failed",
                        message=error_detail,
                        metadata={
                            "exit_code": exit_code,
                            "timed_out": timed_out,
                            "output_file_count": len(output_files),
                        },
                    )
        except Exception as exc:
            raise PersistenceWriteError(
                "Failed to code sandbox execution fail."
            ) from exc

    def mark_execution_denied(
        self,
        execution_id: str,
        *,
        updated_at: str,
        finished_at: str,
        error_detail: str,
    ) -> None:
        try:
            with postgres_connect(self._dsn) as conn:
                with conn.transaction():
                    lock_parent_row(
                        conn,
                        table_name="code_sandbox_executions",
                        key_column="id",
                        key_value=execution_id,
                    )
                    cursor = conn.execute(
                        """
                        UPDATE code_sandbox_executions
                        SET status = 'denied',
                            updated_at = %s,
                            finished_at = %s,
                            timed_out = 0,
                            error_detail = %s
                        WHERE id = %s AND status = 'queued'
                        """,
                        (updated_at, finished_at, error_detail, execution_id),
                    )
                    if cursor.rowcount == 0:
                        return
                    self._append_execution_event_in_transaction(
                        conn,
                        execution_id=execution_id,
                        event_type="execution.denied",
                        created_at=finished_at,
                        status="denied",
                        message=error_detail,
                        metadata=None,
                    )
        except Exception as exc:
            raise PersistenceWriteError(
                "Failed to code sandbox execution deny."
            ) from exc

    def mark_execution_cancelled(
        self,
        execution_id: str,
        *,
        updated_at: str,
        finished_at: str,
        error_detail: str,
        output_files: list[dict[str, object]] | None = None,
    ) -> None:
        try:
            with postgres_connect(self._dsn) as conn:
                with conn.transaction():
                    lock_parent_row(
                        conn,
                        table_name="code_sandbox_executions",
                        key_column="id",
                        key_value=execution_id,
                    )
                    cursor = conn.execute(
                        """
                        UPDATE code_sandbox_executions
                        SET status = 'cancelled',
                            updated_at = %s,
                            finished_at = %s,
                            timed_out = 0,
                            error_detail = %s,
                            output_files_json = %s
                        WHERE id = %s AND status IN ('queued', 'running')
                        """,
                        (
                            updated_at,
                            finished_at,
                            error_detail,
                            encode_json(output_files or []),
                            execution_id,
                        ),
                    )
                    if cursor.rowcount == 0:
                        return
                    self._append_execution_event_in_transaction(
                        conn,
                        execution_id=execution_id,
                        event_type="execution.cancelled",
                        created_at=finished_at,
                        status="cancelled",
                        message=error_detail,
                        metadata=None,
                    )
        except Exception as exc:
            raise PersistenceWriteError(
                "Failed to code sandbox execution cancel."
            ) from exc

    def get_execution(self, execution_id: str) -> CodeSandboxExecutionRecord | None:
        try:
            with postgres_connect(self._dsn) as conn:
                row = conn.execute(
                    """
                    SELECT
                        id,
                        status,
                        execution_mode,
                        runtime_preset,
                        network_policy,
                        timeout_sec,
                        code,
                        command,
                        stdin_text,
                        inline_files_json,
                        created_at,
                        queued_at,
                        updated_at,
                        started_at,
                        finished_at,
                        exit_code,
                        stdout,
                        stderr,
                        timed_out,
                        error_detail,
                        output_files_json,
                        provider_name,
                        last_log_seq,
                        owner_id,
                        tenant_id,
                        principal_id,
                        auth_scopes_json,
                        credential_id,
                        auth_mode
                    FROM code_sandbox_executions
                    WHERE id = %s
                    """,
                    (execution_id,),
                ).fetchone()
        except Exception as exc:
            raise PersistenceReadError(
                "Failed to code sandbox execution read."
            ) from exc
        if row is None:
            return None
        return self._row_to_execution(row)

    def list_execution_events(
        self, execution_id: str
    ) -> list[CodeSandboxExecutionEventRecord]:
        try:
            with postgres_connect(self._dsn) as conn:
                rows = conn.execute(
                    """
                    SELECT execution_id, seq, event_type, created_at, status, message, metadata_json
                    FROM code_sandbox_execution_events
                    WHERE execution_id = %s
                    ORDER BY seq ASC
                    """,
                    (execution_id,),
                ).fetchall()
        except Exception as exc:
            raise PersistenceReadError(
                "Failed to code sandbox execution events list."
            ) from exc
        return [
            CodeSandboxExecutionEventRecord(
                execution_id=str(row["execution_id"]),
                sequence=int(row["seq"]),
                event_type=str(row["event_type"]),
                created_at=str(row["created_at"]),
                status=str(row["status"]) if row["status"] is not None else None,
                message=str(row["message"]) if row["message"] is not None else None,
                metadata=decode_object(row["metadata_json"]),
            )
            for row in rows
        ]

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
            with postgres_connect(self._dsn) as conn:
                with conn.transaction():
                    self._append_execution_event_in_transaction(
                        conn,
                        execution_id=execution_id,
                        event_type=event_type,
                        created_at=created_at,
                        status=status,
                        message=message,
                        metadata=metadata,
                    )
        except Exception as exc:
            raise PersistenceWriteError(
                "Failed to code sandbox execution event append."
            ) from exc

    def append_log_chunk(
        self,
        execution_id: str,
        *,
        created_at: str,
        stream_name: LogStreamName,
        chunk_text: str,
    ) -> int:
        if stream_name not in {"stdout", "stderr"}:
            raise PersistenceWriteError(
                "Failed to code sandbox log chunk append."
            ) from ValueError("Unsupported log stream")
        try:
            with postgres_connect(self._dsn) as conn:
                with conn.transaction():
                    lock_parent_row(
                        conn,
                        table_name="code_sandbox_executions",
                        key_column="id",
                        key_value=execution_id,
                    )
                    next_seq = next_scoped_sequence(
                        conn,
                        table_name="code_sandbox_execution_logs",
                        scope_column="execution_id",
                        scope_value=execution_id,
                    )
                    conn.execute(
                        """
                        INSERT INTO code_sandbox_execution_logs (
                            execution_id,
                            seq,
                            stream_name,
                            created_at,
                            chunk_text
                        ) VALUES (%s, %s, %s, %s, %s)
                        """,
                        (execution_id, next_seq, stream_name, created_at, chunk_text),
                    )
                    conn.execute(
                        f"""
                        UPDATE code_sandbox_executions
                        SET updated_at = %s,
                            last_log_seq = %s,
                            {stream_name} = COALESCE({stream_name}, '') || %s
                        WHERE id = %s
                        """,
                        (created_at, next_seq, chunk_text, execution_id),
                    )
                    self._append_execution_event_in_transaction(
                        conn,
                        execution_id=execution_id,
                        event_type=f"execution.log.{stream_name}",
                        created_at=created_at,
                        status="running",
                        message=None,
                        metadata={
                            "log_sequence": next_seq,
                            "stream_name": stream_name,
                            "byte_size": len(chunk_text.encode("utf-8")),
                        },
                    )
                    return next_seq
        except Exception as exc:
            raise PersistenceWriteError(
                "Failed to code sandbox log chunk append."
            ) from exc

    def list_log_chunks(
        self, execution_id: str, *, after_sequence: int = 0
    ) -> list[CodeSandboxLogChunkRecord]:
        try:
            with postgres_connect(self._dsn) as conn:
                rows = conn.execute(
                    """
                    SELECT execution_id, seq, stream_name, created_at, chunk_text
                    FROM code_sandbox_execution_logs
                    WHERE execution_id = %s AND seq > %s
                    ORDER BY seq ASC
                    """,
                    (execution_id, after_sequence),
                ).fetchall()
        except Exception as exc:
            raise PersistenceReadError(
                "Failed to code sandbox log chunks list."
            ) from exc
        return [
            CodeSandboxLogChunkRecord(
                execution_id=str(row["execution_id"]),
                sequence=int(row["seq"]),
                stream_name=str(row["stream_name"]),
                created_at=str(row["created_at"]),
                chunk_text=str(row["chunk_text"]),
            )
            for row in rows
        ]

    def list_execution_ids_by_status(self, *statuses: str) -> list[str]:
        if not statuses:
            return []
        try:
            with postgres_connect(self._dsn) as conn:
                rows = conn.execute(
                    """
                    SELECT id
                    FROM code_sandbox_executions
                    WHERE status = ANY(%s)
                    ORDER BY queued_at ASC, created_at ASC, id ASC
                    """,
                    (list(statuses),),
                ).fetchall()
        except Exception as exc:
            raise PersistenceReadError(
                "Failed to code sandbox execution status list."
            ) from exc
        return [str(row["id"]) for row in rows]

    def _append_execution_event_in_transaction(
        self,
        conn,
        *,
        execution_id: str,
        event_type: str,
        created_at: str,
        status: str | None,
        message: str | None,
        metadata: dict[str, object] | None,
    ) -> None:
        lock_parent_row(
            conn,
            table_name="code_sandbox_executions",
            key_column="id",
            key_value=execution_id,
        )
        seq = next_scoped_sequence(
            conn,
            table_name="code_sandbox_execution_events",
            scope_column="execution_id",
            scope_value=execution_id,
        )
        conn.execute(
            """
            INSERT INTO code_sandbox_execution_events (
                execution_id,
                seq,
                event_type,
                created_at,
                status,
                message,
                metadata_json
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                execution_id,
                seq,
                event_type,
                created_at,
                status,
                message,
                encode_json(metadata, sort_keys=True) if metadata is not None else None,
            ),
        )

    def _row_to_execution(self, row) -> CodeSandboxExecutionRecord:
        return CodeSandboxExecutionRecord(
            id=str(row["id"]),
            status=str(row["status"]),
            execution_mode=str(row["execution_mode"]),
            runtime_preset=str(row["runtime_preset"]),
            network_policy=str(row["network_policy"]),
            timeout_sec=int(row["timeout_sec"]),
            code=str(row["code"]) if row["code"] is not None else None,
            command=str(row["command"]) if row["command"] is not None else None,
            stdin=str(row["stdin_text"]) if row["stdin_text"] is not None else None,
            inline_files=decode_files(row["inline_files_json"]),
            created_at=str(row["created_at"]),
            queued_at=str(row["queued_at"]),
            updated_at=str(row["updated_at"]),
            started_at=str(row["started_at"])
            if row["started_at"] is not None
            else None,
            finished_at=str(row["finished_at"])
            if row["finished_at"] is not None
            else None,
            exit_code=int(row["exit_code"]) if row["exit_code"] is not None else None,
            stdout=str(row["stdout"] or ""),
            stderr=str(row["stderr"] or ""),
            timed_out=bool(row["timed_out"]),
            error_detail=str(row["error_detail"])
            if row["error_detail"] is not None
            else None,
            output_files=decode_files(row["output_files_json"]),
            provider_name=str(row["provider_name"] or ""),
            last_log_seq=int(row["last_log_seq"] or 0),
            owner_id=str(row["owner_id"] or ""),
            tenant_id=str(row["tenant_id"] or "tenant:default"),
            principal_id=str(row["principal_id"] or ""),
            auth_scopes=decode_string_list(row["auth_scopes_json"]),
            credential_id=str(row["credential_id"] or ""),
            auth_mode=str(row["auth_mode"] or ""),
        )
