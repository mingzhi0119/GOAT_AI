from __future__ import annotations

import sqlite3
from pathlib import Path

from backend.services.sqlite_persistence_utils import (
    decode_object,
    encode_json,
    next_scoped_sequence,
    raise_read_error,
    raise_write_error,
)
from backend.services.workbench_runtime import (
    WorkbenchWorkspaceOutputCreatePayload,
    WorkbenchWorkspaceOutputRecord,
)


class SQLiteWorkbenchWorkspaceOutputStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def create_workspace_output(
        self, payload: WorkbenchWorkspaceOutputCreatePayload
    ) -> WorkbenchWorkspaceOutputRecord:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                self.create_workspace_output_in_transaction(conn, payload)
                conn.commit()
        except Exception as exc:
            raise_write_error("workbench_workspace_output_create", exc)

        return WorkbenchWorkspaceOutputRecord(
            id=payload.output_id,
            task_id=payload.task_id,
            output_kind=payload.output_kind,
            title=payload.title,
            content_format=payload.content_format,
            content_text=payload.content_text,
            created_at=payload.created_at,
            updated_at=payload.updated_at,
            metadata=dict(payload.metadata or {}),
            owner_id=payload.owner_id,
            tenant_id=payload.tenant_id,
            principal_id=payload.principal_id,
        )

    def create_workspace_output_in_transaction(
        self,
        conn: sqlite3.Connection,
        payload: WorkbenchWorkspaceOutputCreatePayload,
    ) -> None:
        metadata_json = (
            encode_json(payload.metadata, sort_keys=True) if payload.metadata else None
        )
        conn.execute(
            """
            INSERT INTO workbench_workspace_outputs (
                id,
                task_id,
                output_kind,
                title,
                content_format,
                content_text,
                metadata_json,
                created_at,
                updated_at,
                owner_id,
                tenant_id,
                principal_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.output_id,
                payload.task_id,
                payload.output_kind,
                payload.title,
                payload.content_format,
                payload.content_text,
                metadata_json,
                payload.created_at,
                payload.updated_at,
                payload.owner_id,
                payload.tenant_id,
                payload.principal_id,
            ),
        )
        self._append_task_event(
            conn,
            task_id=payload.task_id,
            event_type="workspace_output.created",
            created_at=payload.created_at,
            status="running",
            message=f"Workspace output {payload.output_id} created.",
            metadata={
                "output_id": payload.output_id,
                "output_kind": payload.output_kind,
                "content_format": payload.content_format,
            },
        )

    def list_workspace_outputs(
        self, task_id: str
    ) -> list[WorkbenchWorkspaceOutputRecord]:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """
                    SELECT
                        outputs.id,
                        outputs.task_id,
                        outputs.output_kind,
                        outputs.title,
                        outputs.content_format,
                        outputs.content_text,
                        outputs.metadata_json,
                        outputs.created_at,
                        outputs.updated_at,
                        tasks.session_id,
                        tasks.project_id,
                        outputs.owner_id,
                        outputs.tenant_id,
                        outputs.principal_id
                    FROM workbench_workspace_outputs AS outputs
                    JOIN workbench_tasks AS tasks
                      ON tasks.id = outputs.task_id
                    WHERE outputs.task_id = ?
                    ORDER BY outputs.created_at ASC, outputs.id ASC
                    """,
                    (task_id,),
                ).fetchall()
        except Exception as exc:
            raise_read_error("workbench_workspace_outputs_list", exc)
        return [self._row_to_workspace_output(row) for row in rows]

    def get_workspace_output(
        self, output_id: str
    ) -> WorkbenchWorkspaceOutputRecord | None:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    """
                    SELECT
                        outputs.id,
                        outputs.task_id,
                        outputs.output_kind,
                        outputs.title,
                        outputs.content_format,
                        outputs.content_text,
                        outputs.metadata_json,
                        outputs.created_at,
                        outputs.updated_at,
                        tasks.session_id,
                        tasks.project_id,
                        outputs.owner_id,
                        outputs.tenant_id,
                        outputs.principal_id
                    FROM workbench_workspace_outputs AS outputs
                    JOIN workbench_tasks AS tasks
                      ON tasks.id = outputs.task_id
                    WHERE outputs.id = ?
                    """,
                    (output_id,),
                ).fetchone()
        except Exception as exc:
            raise_read_error("workbench_workspace_output_get", exc)
        if row is None:
            return None
        return self._row_to_workspace_output(row)

    def replace_workspace_output_metadata(
        self,
        output_id: str,
        *,
        metadata: dict[str, object],
        updated_at: str,
    ) -> None:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                cursor = conn.execute(
                    """
                    UPDATE workbench_workspace_outputs
                    SET metadata_json = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (encode_json(metadata, sort_keys=True), updated_at, output_id),
                )
                if cursor.rowcount == 0:
                    conn.rollback()
                    return
                conn.commit()
        except Exception as exc:
            raise_write_error("workbench_workspace_output_metadata_replace", exc)

    def list_workspace_outputs_for_session(
        self, session_id: str
    ) -> list[WorkbenchWorkspaceOutputRecord]:
        return self._list_workspace_outputs_by_scope(
            column_name="tasks.session_id",
            scope_value=session_id,
            operation="workbench_workspace_outputs_session_list",
        )

    def list_workspace_outputs_for_project(
        self, project_id: str
    ) -> list[WorkbenchWorkspaceOutputRecord]:
        return self._list_workspace_outputs_by_scope(
            column_name="tasks.project_id",
            scope_value=project_id,
            operation="workbench_workspace_outputs_project_list",
        )

    def _append_task_event(
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

    def _list_workspace_outputs_by_scope(
        self, *, column_name: str, scope_value: str, operation: str
    ) -> list[WorkbenchWorkspaceOutputRecord]:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    f"""
                    SELECT
                        outputs.id,
                        outputs.task_id,
                        outputs.output_kind,
                        outputs.title,
                        outputs.content_format,
                        outputs.content_text,
                        outputs.metadata_json,
                        outputs.created_at,
                        outputs.updated_at,
                        tasks.session_id,
                        tasks.project_id,
                        outputs.owner_id,
                        outputs.tenant_id,
                        outputs.principal_id
                    FROM workbench_workspace_outputs AS outputs
                    JOIN workbench_tasks AS tasks
                      ON tasks.id = outputs.task_id
                    WHERE {column_name} = ?
                    ORDER BY outputs.updated_at DESC, outputs.id ASC
                    """,
                    (scope_value,),
                ).fetchall()
        except Exception as exc:
            raise_read_error(operation, exc)
        return [self._row_to_workspace_output(row) for row in rows]

    def _row_to_workspace_output(
        self, row: sqlite3.Row
    ) -> WorkbenchWorkspaceOutputRecord:
        return WorkbenchWorkspaceOutputRecord(
            id=str(row["id"]),
            task_id=str(row["task_id"]),
            output_kind=str(row["output_kind"]),
            title=str(row["title"]),
            content_format=str(row["content_format"]),
            content_text=str(row["content_text"]),
            metadata=decode_object(row["metadata_json"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            session_id=str(row["session_id"])
            if row["session_id"] is not None
            else None,
            project_id=str(row["project_id"])
            if row["project_id"] is not None
            else None,
            owner_id=str(row["owner_id"] or ""),
            tenant_id=str(row["tenant_id"] or "tenant:default"),
            principal_id=str(row["principal_id"] or ""),
        )
