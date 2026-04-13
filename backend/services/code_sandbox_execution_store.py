from __future__ import annotations

import sqlite3
from pathlib import Path

from backend.services.code_sandbox_runtime import (
    CodeSandboxExecutionCreatePayload,
    CodeSandboxExecutionEventRecord,
    CodeSandboxExecutionRecord,
)
from backend.services.sqlite_persistence_utils import (
    decode_files,
    decode_object,
    decode_string_list,
    encode_json,
    next_scoped_sequence,
    raise_read_error,
    raise_write_error,
)


class SQLiteCodeSandboxExecutionStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def create_execution(
        self, payload: CodeSandboxExecutionCreatePayload
    ) -> CodeSandboxExecutionRecord:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                self.create_execution_in_transaction(conn, payload)
                conn.commit()
        except Exception as exc:
            raise_write_error("code_sandbox_execution_create", exc)
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
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                updated = self.mark_execution_started_in_transaction(
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
                updated = self.mark_execution_completed_in_transaction(
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
                updated = self.mark_execution_failed_in_transaction(
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
                updated = self.mark_execution_denied_in_transaction(
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
                updated = self.mark_execution_cancelled_in_transaction(
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
        try:
            with sqlite3.connect(self._db_path) as conn:
                row = self._fetch_execution_row(conn, execution_id)
        except Exception as exc:
            raise_read_error("code_sandbox_execution_read", exc)
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
            raise_read_error("code_sandbox_execution_events_list", exc)
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
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                self.append_execution_event_in_transaction(
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

    def create_execution_in_transaction(
        self,
        conn: sqlite3.Connection,
        payload: CodeSandboxExecutionCreatePayload,
    ) -> None:
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
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, '', '', 0, NULL, NULL, ?, 0, ?, ?, ?, ?, ?, ?)
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
        self.append_execution_event_in_transaction(
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

    def mark_execution_started_in_transaction(
        self,
        conn: sqlite3.Connection,
        execution_id: str,
        *,
        updated_at: str,
        provider_name: str,
    ) -> bool:
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
            return False
        self.append_execution_event_in_transaction(
            conn,
            execution_id=execution_id,
            event_type="execution.started",
            created_at=updated_at,
            status="running",
            message="Execution started.",
            metadata={"provider_name": provider_name},
        )
        return True

    def mark_execution_completed_in_transaction(
        self,
        conn: sqlite3.Connection,
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
    ) -> bool:
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
                encode_json(output_files),
                execution_id,
            ),
        )
        if cursor.rowcount == 0:
            return False
        self.append_execution_event_in_transaction(
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
        return True

    def mark_execution_failed_in_transaction(
        self,
        conn: sqlite3.Connection,
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
    ) -> bool:
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
                encode_json(output_files),
                execution_id,
            ),
        )
        if cursor.rowcount == 0:
            return False
        event_type = "execution.timed_out" if timed_out else "execution.failed"
        self.append_execution_event_in_transaction(
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
        return True

    def mark_execution_denied_in_transaction(
        self,
        conn: sqlite3.Connection,
        execution_id: str,
        *,
        updated_at: str,
        finished_at: str,
        error_detail: str,
    ) -> bool:
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
            return False
        self.append_execution_event_in_transaction(
            conn,
            execution_id=execution_id,
            event_type="execution.denied",
            created_at=finished_at,
            status="denied",
            message=error_detail,
            metadata=None,
        )
        return True

    def mark_execution_cancelled_in_transaction(
        self,
        conn: sqlite3.Connection,
        execution_id: str,
        *,
        updated_at: str,
        finished_at: str,
        error_detail: str,
        output_files: list[dict[str, object]] | None = None,
    ) -> bool:
        cursor = conn.execute(
            """
            UPDATE code_sandbox_executions
            SET status = 'cancelled',
                updated_at = ?,
                finished_at = ?,
                timed_out = 0,
                error_detail = ?,
                output_files_json = ?
            WHERE id = ? AND status IN ('queued', 'running')
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
            return False
        self.append_execution_event_in_transaction(
            conn,
            execution_id=execution_id,
            event_type="execution.cancelled",
            created_at=finished_at,
            status="cancelled",
            message=error_detail,
            metadata=None,
        )
        return True

    def append_execution_event_in_transaction(
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
        self._append_event(
            conn,
            execution_id=execution_id,
            event_type=event_type,
            created_at=created_at,
            status=status,
            message=message,
            metadata=metadata,
        )

    def list_execution_ids_by_status(self, *statuses: str) -> list[str]:
        if not statuses:
            return []
        placeholders = ", ".join("?" for _ in statuses)
        try:
            with sqlite3.connect(self._db_path) as conn:
                rows = conn.execute(
                    f"""
                    SELECT id
                    FROM code_sandbox_executions
                    WHERE status IN ({placeholders})
                    ORDER BY queued_at ASC, created_at ASC, id ASC
                    """,
                    statuses,
                ).fetchall()
        except Exception as exc:
            raise_read_error("code_sandbox_execution_status_list", exc)
        return [str(row[0]) for row in rows]

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
                next_scoped_sequence(
                    conn,
                    table="code_sandbox_execution_events",
                    scope_column="execution_id",
                    scope_value=execution_id,
                ),
                event_type,
                created_at,
                status,
                message,
                encode_json(metadata, sort_keys=True) if metadata is not None else None,
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
            WHERE id = ?
            """,
            (execution_id,),
        ).fetchone()

    def _row_to_execution(self, row: sqlite3.Row) -> CodeSandboxExecutionRecord:
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
