from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

from backend.services.sqlite_persistence_utils import (
    decode_object,
    decode_object_list,
    decode_string_list,
    encode_json,
    next_scoped_sequence,
    raise_read_error,
    raise_write_error,
)
from backend.services.workbench_runtime import (
    WorkbenchTaskCreatePayload,
    WorkbenchTaskEventRecord,
    WorkbenchTaskRecord,
)


class SQLiteWorkbenchTaskStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def create_task(self, payload: WorkbenchTaskCreatePayload) -> WorkbenchTaskRecord:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                self.create_task_in_transaction(conn, payload)
                conn.commit()
        except Exception as exc:
            raise_write_error("workbench_task_create", exc)

        return WorkbenchTaskRecord(
            id=payload.task_id,
            task_kind=payload.task_kind,
            status=payload.status,
            prompt=payload.prompt,
            session_id=payload.session_id,
            project_id=payload.project_id,
            knowledge_document_ids=list(payload.knowledge_document_ids),
            connector_ids=list(payload.connector_ids),
            source_ids=list(payload.source_ids),
            created_at=payload.created_at,
            updated_at=payload.updated_at,
            error_detail=payload.error_detail,
            result_text=None,
            result_citations=None,
            auth_scopes=list(payload.auth_scopes or []),
            credential_id=payload.credential_id,
            auth_mode=payload.auth_mode,
            owner_id=payload.owner_id,
            tenant_id=payload.tenant_id,
            principal_id=payload.principal_id,
        )

    def claim_task_for_execution(
        self, task_id: str, *, updated_at: str
    ) -> WorkbenchTaskRecord | None:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                claimed = self.claim_task_for_execution_in_transaction(
                    conn, task_id, updated_at=updated_at
                )
                if not claimed:
                    conn.rollback()
                    return None
                conn.commit()
        except Exception as exc:
            raise_write_error("workbench_task_claim", exc)
        return self.get_task(task_id)

    def mark_task_completed(
        self,
        task_id: str,
        *,
        updated_at: str,
        result_text: str,
        result_citations: list[dict[str, object]] | None = None,
        workspace_output_count: int | None = None,
    ) -> None:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                updated = self.mark_task_completed_in_transaction(
                    conn,
                    task_id,
                    updated_at=updated_at,
                    result_text=result_text,
                    result_citations=result_citations,
                    workspace_output_count=workspace_output_count,
                )
                if not updated:
                    conn.rollback()
                    return
                conn.commit()
        except Exception as exc:
            raise_write_error("workbench_task_complete", exc)

    def mark_task_failed(
        self, task_id: str, *, updated_at: str, error_detail: str
    ) -> None:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                updated = self.mark_task_failed_in_transaction(
                    conn, task_id, updated_at=updated_at, error_detail=error_detail
                )
                if not updated:
                    conn.rollback()
                    return
                conn.commit()
        except Exception as exc:
            raise_write_error("workbench_task_fail", exc)

    def mark_task_cancelled(
        self, task_id: str, *, updated_at: str, error_detail: str
    ) -> None:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                updated = self.mark_task_cancelled_in_transaction(
                    conn, task_id, updated_at=updated_at, error_detail=error_detail
                )
                if not updated:
                    conn.rollback()
                    return
                conn.commit()
        except Exception as exc:
            raise_write_error("workbench_task_cancel", exc)

    def get_task(self, task_id: str) -> WorkbenchTaskRecord | None:
        try:
            with sqlite3.connect(self._db_path) as conn:
                row = self._fetch_task_row(conn, task_id)
        except Exception as exc:
            raise_read_error("workbench_task_get", exc)
        if row is None:
            return None
        return self._row_to_task(row)

    def list_task_ids_by_status(self, statuses: Iterable[str]) -> list[str]:
        normalized = [str(status).strip() for status in statuses if str(status).strip()]
        if not normalized:
            return []
        placeholders = ", ".join("?" for _ in normalized)
        try:
            with sqlite3.connect(self._db_path) as conn:
                rows = conn.execute(
                    f"""
                    SELECT id
                    FROM workbench_tasks
                    WHERE status IN ({placeholders})
                    ORDER BY created_at ASC, id ASC
                    """,
                    tuple(normalized),
                ).fetchall()
        except Exception as exc:
            raise_read_error("workbench_task_ids_list", exc)
        return [str(row[0]) for row in rows]

    def list_task_events(self, task_id: str) -> list[WorkbenchTaskEventRecord]:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """
                    SELECT
                        task_id,
                        seq,
                        event_type,
                        created_at,
                        status,
                        message,
                        metadata_json
                    FROM workbench_task_events
                    WHERE task_id = ?
                    ORDER BY seq ASC
                    """,
                    (task_id,),
                ).fetchall()
        except Exception as exc:
            raise_read_error("workbench_task_events_list", exc)
        return [self._row_to_event(row) for row in rows]

    def append_task_event(
        self,
        task_id: str,
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
                self.append_task_event_in_transaction(
                    conn,
                    task_id=task_id,
                    event_type=event_type,
                    created_at=created_at,
                    status=status,
                    message=message,
                    metadata=metadata,
                )
                conn.commit()
        except Exception as exc:
            raise_write_error("workbench_task_event_append", exc)

    def create_task_in_transaction(
        self,
        conn: sqlite3.Connection,
        payload: WorkbenchTaskCreatePayload,
    ) -> None:
        conn.execute(
            """
            INSERT INTO workbench_tasks (
                id,
                task_kind,
                status,
                prompt,
                session_id,
                project_id,
                knowledge_document_ids,
                connector_ids,
                source_ids,
                error_detail,
                result_text,
                result_citations_json,
                created_at,
                updated_at,
                auth_scopes_json,
                credential_id,
                auth_mode,
                owner_id,
                tenant_id,
                principal_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.task_id,
                payload.task_kind,
                payload.status,
                payload.prompt,
                payload.session_id,
                payload.project_id,
                encode_json(payload.knowledge_document_ids),
                encode_json(payload.connector_ids),
                encode_json(payload.source_ids),
                payload.error_detail,
                None,
                None,
                payload.created_at,
                payload.updated_at,
                encode_json(payload.auth_scopes or []),
                payload.credential_id,
                payload.auth_mode,
                payload.owner_id,
                payload.tenant_id,
                payload.principal_id,
            ),
        )
        self.append_task_event_in_transaction(
            conn,
            task_id=payload.task_id,
            event_type="task.queued",
            created_at=payload.created_at,
            status=payload.status,
            message="Task accepted.",
            metadata={
                "task_kind": payload.task_kind,
                "project_id": payload.project_id,
                "session_id": payload.session_id,
                "source_ids": list(payload.source_ids),
            },
        )

    def claim_task_for_execution_in_transaction(
        self,
        conn: sqlite3.Connection,
        task_id: str,
        *,
        updated_at: str,
    ) -> bool:
        current = self._fetch_task_row(conn, task_id)
        if current is None:
            return False
        cursor = conn.execute(
            """
            UPDATE workbench_tasks
            SET status = 'running', updated_at = ?
            WHERE id = ? AND status = 'queued'
            """,
            (updated_at, task_id),
        )
        if cursor.rowcount == 0:
            return False
        self.append_task_event_in_transaction(
            conn,
            task_id=task_id,
            event_type="task.started",
            created_at=updated_at,
            status="running",
            message="Task execution started.",
            metadata={"task_kind": str(current["task_kind"])},
        )
        return True

    def mark_task_completed_in_transaction(
        self,
        conn: sqlite3.Connection,
        task_id: str,
        *,
        updated_at: str,
        result_text: str,
        result_citations: list[dict[str, object]] | None = None,
        workspace_output_count: int | None = None,
    ) -> bool:
        citations_json = (
            encode_json(result_citations, sort_keys=True) if result_citations else None
        )
        cursor = conn.execute(
            """
            UPDATE workbench_tasks
            SET status = 'completed',
                updated_at = ?,
                error_detail = NULL,
                result_text = ?,
                result_citations_json = ?
            WHERE id = ? AND status = 'running'
            """,
            (updated_at, result_text, citations_json, task_id),
        )
        if cursor.rowcount == 0:
            return False
        self.append_task_event_in_transaction(
            conn,
            task_id=task_id,
            event_type="task.completed",
            created_at=updated_at,
            status="completed",
            message="Task execution completed.",
            metadata={
                "result_format": "markdown",
                "citation_count": len(result_citations or []),
                "workspace_output_count": int(workspace_output_count or 0),
            },
        )
        return True

    def mark_task_failed_in_transaction(
        self,
        conn: sqlite3.Connection,
        task_id: str,
        *,
        updated_at: str,
        error_detail: str,
    ) -> bool:
        cursor = conn.execute(
            """
            UPDATE workbench_tasks
            SET status = 'failed',
                updated_at = ?,
                error_detail = ?,
                result_text = NULL,
                result_citations_json = NULL
            WHERE id = ? AND status IN ('queued', 'running')
            """,
            (updated_at, error_detail, task_id),
        )
        if cursor.rowcount == 0:
            return False
        self.append_task_event_in_transaction(
            conn,
            task_id=task_id,
            event_type="task.failed",
            created_at=updated_at,
            status="failed",
            message=error_detail,
            metadata={},
        )
        return True

    def mark_task_cancelled_in_transaction(
        self,
        conn: sqlite3.Connection,
        task_id: str,
        *,
        updated_at: str,
        error_detail: str,
    ) -> bool:
        cursor = conn.execute(
            """
            UPDATE workbench_tasks
            SET status = 'cancelled',
                updated_at = ?,
                error_detail = ?,
                result_text = NULL,
                result_citations_json = NULL
            WHERE id = ? AND status = 'queued'
            """,
            (updated_at, error_detail, task_id),
        )
        if cursor.rowcount == 0:
            return False
        self.append_task_event_in_transaction(
            conn,
            task_id=task_id,
            event_type="task.cancelled",
            created_at=updated_at,
            status="cancelled",
            message=error_detail,
            metadata={},
        )
        return True

    def append_task_event_in_transaction(
        self,
        conn: sqlite3.Connection,
        *,
        task_id: str,
        event_type: str,
        created_at: str,
        status: str | None,
        message: str | None,
        metadata: dict[str, object] | None,
    ) -> None:
        self._append_event(
            conn,
            task_id=task_id,
            event_type=event_type,
            created_at=created_at,
            status=status,
            message=message,
            metadata=metadata,
        )

    def _fetch_task_row(
        self, conn: sqlite3.Connection, task_id: str
    ) -> sqlite3.Row | None:
        conn.row_factory = sqlite3.Row
        return conn.execute(
            """
            SELECT
                id,
                task_kind,
                status,
                prompt,
                session_id,
                project_id,
                knowledge_document_ids,
                connector_ids,
                source_ids,
                error_detail,
                result_text,
                result_citations_json,
                created_at,
                updated_at,
                auth_scopes_json,
                credential_id,
                auth_mode,
                owner_id,
                tenant_id,
                principal_id
            FROM workbench_tasks
            WHERE id = ?
            """,
            (task_id,),
        ).fetchone()

    def _append_event(
        self,
        conn: sqlite3.Connection,
        *,
        task_id: str,
        event_type: str,
        created_at: str,
        status: str | None,
        message: str | None,
        metadata: dict[str, object] | None,
    ) -> None:
        conn.execute(
            """
            INSERT INTO workbench_task_events (
                task_id,
                seq,
                event_type,
                created_at,
                status,
                message,
                metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                next_scoped_sequence(
                    conn,
                    table="workbench_task_events",
                    scope_column="task_id",
                    scope_value=task_id,
                ),
                event_type,
                created_at,
                status,
                message,
                encode_json(metadata, sort_keys=True) if metadata is not None else None,
            ),
        )

    def _row_to_task(self, row: sqlite3.Row) -> WorkbenchTaskRecord:
        return WorkbenchTaskRecord(
            id=str(row["id"]),
            task_kind=str(row["task_kind"]),
            status=str(row["status"]),
            prompt=str(row["prompt"]),
            session_id=str(row["session_id"])
            if row["session_id"] is not None
            else None,
            project_id=str(row["project_id"])
            if row["project_id"] is not None
            else None,
            knowledge_document_ids=decode_string_list(row["knowledge_document_ids"]),
            connector_ids=decode_string_list(row["connector_ids"]),
            source_ids=decode_string_list(row["source_ids"]),
            error_detail=str(row["error_detail"])
            if row["error_detail"] is not None
            else None,
            result_text=str(row["result_text"])
            if row["result_text"] is not None
            else None,
            result_citations=decode_object_list(row["result_citations_json"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            auth_scopes=decode_string_list(row["auth_scopes_json"]),
            credential_id=str(row["credential_id"] or ""),
            auth_mode=str(row["auth_mode"] or ""),
            owner_id=str(row["owner_id"] or ""),
            tenant_id=str(row["tenant_id"] or "tenant:default"),
            principal_id=str(row["principal_id"] or ""),
        )

    def _row_to_event(self, row: sqlite3.Row) -> WorkbenchTaskEventRecord:
        return WorkbenchTaskEventRecord(
            task_id=str(row["task_id"]),
            sequence=int(row["seq"]),
            event_type=str(row["event_type"]),
            created_at=str(row["created_at"]),
            status=str(row["status"]) if row["status"] is not None else None,
            message=str(row["message"]) if row["message"] is not None else None,
            metadata=decode_object(row["metadata_json"]),
        )
