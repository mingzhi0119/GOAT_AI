"""SQLite persistence for durable code sandbox executions."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from backend.services.exceptions import PersistenceReadError, PersistenceWriteError


def _raise_read_error(operation: str, exc: Exception) -> None:
    raise PersistenceReadError(f"Failed to {operation.replace('_', ' ')}.") from exc


def _raise_write_error(operation: str, exc: Exception) -> None:
    raise PersistenceWriteError(f"Failed to {operation.replace('_', ' ')}.") from exc


def _decode_string_list(raw: object) -> list[str]:
    if not isinstance(raw, str) or not raw.strip():
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed if isinstance(item, str)]


def _decode_files(raw: object) -> list[dict[str, object]]:
    if not isinstance(raw, str) or not raw.strip():
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    out: list[dict[str, object]] = []
    for item in parsed:
        if isinstance(item, dict):
            out.append({str(key): value for key, value in item.items()})
    return out


@dataclass(frozen=True, kw_only=True)
class CodeSandboxExecutionRecord:
    """Durable code sandbox execution record."""

    id: str
    status: str
    runtime_preset: str
    network_policy: str
    code: str | None
    command: str | None
    stdin: str | None
    inline_files: list[dict[str, object]]
    created_at: str
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
    owner_id: str = ""
    tenant_id: str = "tenant:default"
    principal_id: str = ""
    auth_scopes: list[str] | None = None
    credential_id: str = ""
    auth_mode: str = ""


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
class CodeSandboxExecutionCreatePayload:
    """Initial persisted state for one accepted execution."""

    execution_id: str
    runtime_preset: str
    network_policy: str
    code: str | None
    command: str | None
    stdin: str | None
    inline_files: list[dict[str, object]]
    created_at: str
    updated_at: str
    owner_id: str = ""
    tenant_id: str = "tenant:default"
    principal_id: str = ""
    auth_scopes: list[str] | None = None
    credential_id: str = ""
    auth_mode: str = ""
    status: str = "queued"


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


class SQLiteCodeSandboxExecutionRepository:
    """SQLite-backed persistence for code sandbox executions."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def create_execution(
        self, payload: CodeSandboxExecutionCreatePayload
    ) -> CodeSandboxExecutionRecord:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute(
                    """
                    INSERT INTO code_sandbox_executions (
                        id,
                        status,
                        runtime_preset,
                        network_policy,
                        code,
                        command,
                        stdin_text,
                        inline_files_json,
                        created_at,
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
                        owner_id,
                        tenant_id,
                        principal_id,
                        auth_scopes_json,
                        credential_id,
                        auth_mode
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, '', '', 0, NULL, NULL, '', ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload.execution_id,
                        payload.status,
                        payload.runtime_preset,
                        payload.network_policy,
                        payload.code,
                        payload.command,
                        payload.stdin,
                        json.dumps(payload.inline_files, ensure_ascii=False),
                        payload.created_at,
                        payload.updated_at,
                        payload.owner_id,
                        payload.tenant_id,
                        payload.principal_id,
                        json.dumps(payload.auth_scopes or [], ensure_ascii=False),
                        payload.credential_id,
                        payload.auth_mode,
                    ),
                )
                self._append_event(
                    conn,
                    execution_id=payload.execution_id,
                    event_type="execution.queued",
                    created_at=payload.created_at,
                    status=payload.status,
                    message="Execution accepted.",
                    metadata={
                        "network_policy": payload.network_policy,
                        "runtime_preset": payload.runtime_preset,
                    },
                )
                conn.commit()
        except Exception as exc:
            _raise_write_error("code_sandbox_execution_create", exc)
        return self.get_execution(payload.execution_id) or CodeSandboxExecutionRecord(
            id=payload.execution_id,
            status=payload.status,
            runtime_preset=payload.runtime_preset,
            network_policy=payload.network_policy,
            code=payload.code,
            command=payload.command,
            stdin=payload.stdin,
            inline_files=list(payload.inline_files),
            created_at=payload.created_at,
            updated_at=payload.updated_at,
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
                cursor = conn.execute(
                    """
                    UPDATE code_sandbox_executions
                    SET status = 'running',
                        updated_at = ?,
                        started_at = COALESCE(started_at, ?),
                        provider_name = ?
                    WHERE id = ? AND status = 'queued'
                    """,
                    (updated_at, updated_at, provider_name, execution_id),
                )
                if cursor.rowcount == 0:
                    conn.rollback()
                    return None
                self._append_event(
                    conn,
                    execution_id=execution_id,
                    event_type="execution.started",
                    created_at=updated_at,
                    status="running",
                    message="Execution started.",
                    metadata={"provider_name": provider_name},
                )
                conn.commit()
        except Exception as exc:
            _raise_write_error("code_sandbox_execution_start", exc)
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
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                cursor = conn.execute(
                    """
                    UPDATE code_sandbox_executions
                    SET status = 'completed',
                        updated_at = ?,
                        finished_at = ?,
                        exit_code = ?,
                        stdout = ?,
                        stderr = ?,
                        timed_out = ?,
                        error_detail = ?,
                        output_files_json = ?
                    WHERE id = ? AND status = 'running'
                    """,
                    (
                        updated_at,
                        finished_at,
                        exit_code,
                        stdout,
                        stderr,
                        1 if timed_out else 0,
                        error_detail,
                        json.dumps(output_files, ensure_ascii=False),
                        execution_id,
                    ),
                )
                if cursor.rowcount == 0:
                    conn.rollback()
                    return
                self._append_event(
                    conn,
                    execution_id=execution_id,
                    event_type="execution.completed",
                    created_at=finished_at,
                    status="completed",
                    message="Execution completed successfully.",
                    metadata={
                        "exit_code": exit_code,
                        "output_file_count": len(output_files),
                    },
                )
                conn.commit()
        except Exception as exc:
            _raise_write_error("code_sandbox_execution_complete", exc)

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
                cursor = conn.execute(
                    """
                    UPDATE code_sandbox_executions
                    SET status = 'failed',
                        updated_at = ?,
                        finished_at = ?,
                        exit_code = ?,
                        stdout = ?,
                        stderr = ?,
                        timed_out = ?,
                        error_detail = ?,
                        output_files_json = ?
                    WHERE id = ? AND status IN ('queued', 'running')
                    """,
                    (
                        updated_at,
                        finished_at,
                        exit_code,
                        stdout,
                        stderr,
                        1 if timed_out else 0,
                        error_detail,
                        json.dumps(output_files, ensure_ascii=False),
                        execution_id,
                    ),
                )
                if cursor.rowcount == 0:
                    conn.rollback()
                    return
                event_type = "execution.timed_out" if timed_out else "execution.failed"
                self._append_event(
                    conn,
                    execution_id=execution_id,
                    event_type=event_type,
                    created_at=finished_at,
                    status="failed",
                    message=error_detail,
                    metadata={
                        "exit_code": exit_code,
                        "timed_out": timed_out,
                        "output_file_count": len(output_files),
                    },
                )
                conn.commit()
        except Exception as exc:
            _raise_write_error("code_sandbox_execution_fail", exc)

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
                cursor = conn.execute(
                    """
                    UPDATE code_sandbox_executions
                    SET status = 'denied',
                        updated_at = ?,
                        finished_at = ?,
                        timed_out = 0,
                        error_detail = ?
                    WHERE id = ? AND status = 'queued'
                    """,
                    (updated_at, finished_at, error_detail, execution_id),
                )
                if cursor.rowcount == 0:
                    conn.rollback()
                    return
                self._append_event(
                    conn,
                    execution_id=execution_id,
                    event_type="execution.denied",
                    created_at=finished_at,
                    status="denied",
                    message=error_detail,
                    metadata=None,
                )
                conn.commit()
        except Exception as exc:
            _raise_write_error("code_sandbox_execution_deny", exc)

    def get_execution(self, execution_id: str) -> CodeSandboxExecutionRecord | None:
        try:
            with sqlite3.connect(self._db_path) as conn:
                row = self._fetch_execution_row(conn, execution_id)
        except Exception as exc:
            _raise_read_error("code_sandbox_execution_read", exc)
        if row is None:
            return None
        return self._row_to_execution(row)

    def list_execution_events(
        self, execution_id: str
    ) -> list[CodeSandboxExecutionEventRecord]:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """
                    SELECT execution_id, seq, event_type, created_at, status, message, metadata_json
                    FROM code_sandbox_execution_events
                    WHERE execution_id = ?
                    ORDER BY seq ASC
                    """,
                    (execution_id,),
                ).fetchall()
        except Exception as exc:
            _raise_read_error("code_sandbox_execution_events_list", exc)
        return [
            CodeSandboxExecutionEventRecord(
                execution_id=str(row["execution_id"]),
                sequence=int(row["seq"]),
                event_type=str(row["event_type"]),
                created_at=str(row["created_at"]),
                status=str(row["status"]) if row["status"] is not None else None,
                message=str(row["message"]) if row["message"] is not None else None,
                metadata=(
                    json.loads(str(row["metadata_json"]))
                    if row["metadata_json"] is not None
                    else None
                ),
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
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                self._append_event(
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
            _raise_write_error("code_sandbox_execution_event_append", exc)

    def _append_event(
        self,
        conn: sqlite3.Connection,
        *,
        execution_id: str,
        event_type: str,
        created_at: str,
        status: str | None,
        message: str | None,
        metadata: dict[str, object] | None,
    ) -> None:
        seq_row = conn.execute(
            "SELECT COALESCE(MAX(seq), 0) + 1 FROM code_sandbox_execution_events WHERE execution_id = ?",
            (execution_id,),
        ).fetchone()
        next_seq = int(seq_row[0]) if seq_row is not None else 1
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
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                execution_id,
                next_seq,
                event_type,
                created_at,
                status,
                message,
                json.dumps(metadata, ensure_ascii=False, sort_keys=True)
                if metadata is not None
                else None,
            ),
        )

    def _fetch_execution_row(
        self,
        conn: sqlite3.Connection,
        execution_id: str,
    ) -> sqlite3.Row | None:
        conn.row_factory = sqlite3.Row
        return conn.execute(
            """
            SELECT
                id,
                status,
                runtime_preset,
                network_policy,
                code,
                command,
                stdin_text,
                inline_files_json,
                created_at,
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
                owner_id,
                tenant_id,
                principal_id,
                auth_scopes_json,
                credential_id,
                auth_mode
            FROM code_sandbox_executions
            WHERE id = ?
            """,
            (execution_id,),
        ).fetchone()

    def _row_to_execution(self, row: sqlite3.Row) -> CodeSandboxExecutionRecord:
        return CodeSandboxExecutionRecord(
            id=str(row["id"]),
            status=str(row["status"]),
            runtime_preset=str(row["runtime_preset"]),
            network_policy=str(row["network_policy"]),
            code=str(row["code"]) if row["code"] is not None else None,
            command=str(row["command"]) if row["command"] is not None else None,
            stdin=str(row["stdin_text"]) if row["stdin_text"] is not None else None,
            inline_files=_decode_files(row["inline_files_json"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            started_at=str(row["started_at"])
            if row["started_at"] is not None
            else None,
            finished_at=(
                str(row["finished_at"]) if row["finished_at"] is not None else None
            ),
            exit_code=int(row["exit_code"]) if row["exit_code"] is not None else None,
            stdout=str(row["stdout"] or ""),
            stderr=str(row["stderr"] or ""),
            timed_out=bool(row["timed_out"]),
            error_detail=(
                str(row["error_detail"]) if row["error_detail"] is not None else None
            ),
            output_files=_decode_files(row["output_files_json"]),
            provider_name=str(row["provider_name"] or ""),
            owner_id=str(row["owner_id"] or ""),
            tenant_id=str(row["tenant_id"] or "tenant:default"),
            principal_id=str(row["principal_id"] or ""),
            auth_scopes=_decode_string_list(row["auth_scopes_json"]),
            credential_id=str(row["credential_id"] or ""),
            auth_mode=str(row["auth_mode"] or ""),
        )
