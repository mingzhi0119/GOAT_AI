"""Typed runtime interfaces and SQLite adapter for workbench task persistence."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol

from backend.domain.resource_ownership import (
    PersistedResourceOwnership,
    ownership_from_fields,
)
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


def _decode_object_list(raw: object) -> list[dict[str, object]] | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, list):
        return None
    out: list[dict[str, object]] = []
    for item in parsed:
        if isinstance(item, dict):
            out.append(item)
    return out


def _decode_object(raw: object) -> dict[str, object] | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


@dataclass(frozen=True, kw_only=True)
class WorkbenchTaskRecord:
    """Durable workbench task record persisted for status polling."""

    id: str
    task_kind: str
    status: str
    prompt: str
    session_id: str | None
    project_id: str | None
    knowledge_document_ids: list[str]
    connector_ids: list[str]
    source_ids: list[str]
    created_at: str
    updated_at: str
    error_detail: str | None = None
    result_text: str | None = None
    result_citations: list[dict[str, object]] | None = None
    auth_scopes: list[str] | None = None
    credential_id: str = ""
    auth_mode: str = ""
    owner_id: str = ""
    tenant_id: str = "tenant:default"
    principal_id: str = ""

    @property
    def ownership(self) -> PersistedResourceOwnership:
        return ownership_from_fields(
            owner_id=self.owner_id,
            tenant_id=self.tenant_id,
            principal_id=self.principal_id,
        )


@dataclass(frozen=True, kw_only=True)
class WorkbenchTaskEventRecord:
    """Durable workbench task event persisted for task timeline polling."""

    task_id: str
    sequence: int
    event_type: str
    created_at: str
    status: str | None = None
    message: str | None = None
    metadata: dict[str, object] | None = None


@dataclass(frozen=True, kw_only=True)
class WorkbenchWorkspaceOutputRecord:
    """Typed durable workspace output linked to one task."""

    id: str
    task_id: str
    output_kind: str
    title: str
    content_format: str
    content_text: str
    created_at: str
    updated_at: str
    metadata: dict[str, object] | None = None
    session_id: str | None = None
    project_id: str | None = None
    owner_id: str = ""
    tenant_id: str = "tenant:default"
    principal_id: str = ""

    @property
    def ownership(self) -> PersistedResourceOwnership:
        return ownership_from_fields(
            owner_id=self.owner_id,
            tenant_id=self.tenant_id,
            principal_id=self.principal_id,
        )


@dataclass(frozen=True, kw_only=True)
class WorkbenchTaskCreatePayload:
    """Payload required to create one durable queued workbench task."""

    task_id: str
    task_kind: str
    prompt: str
    session_id: str | None
    project_id: str | None
    knowledge_document_ids: list[str]
    connector_ids: list[str]
    source_ids: list[str]
    created_at: str
    updated_at: str
    owner_id: str = ""
    tenant_id: str = "tenant:default"
    principal_id: str = ""
    auth_scopes: list[str] | None = None
    credential_id: str = ""
    auth_mode: str = ""
    status: str = "queued"
    error_detail: str | None = None

    @property
    def ownership(self) -> PersistedResourceOwnership:
        return ownership_from_fields(
            owner_id=self.owner_id,
            tenant_id=self.tenant_id,
            principal_id=self.principal_id,
        )


@dataclass(frozen=True, kw_only=True)
class WorkbenchWorkspaceOutputCreatePayload:
    """Payload required to create one durable workspace output."""

    output_id: str
    task_id: str
    output_kind: str
    title: str
    content_format: str
    content_text: str
    created_at: str
    updated_at: str
    metadata: dict[str, object] | None = None
    owner_id: str = ""
    tenant_id: str = "tenant:default"
    principal_id: str = ""

    @property
    def ownership(self) -> PersistedResourceOwnership:
        return ownership_from_fields(
            owner_id=self.owner_id,
            tenant_id=self.tenant_id,
            principal_id=self.principal_id,
        )


class WorkbenchTaskRepository(Protocol):
    """Persistence boundary for durable workbench task records."""

    def create_task(
        self, payload: WorkbenchTaskCreatePayload
    ) -> WorkbenchTaskRecord: ...

    def claim_task_for_execution(
        self, task_id: str, *, updated_at: str
    ) -> WorkbenchTaskRecord | None: ...

    def create_workspace_output(
        self, payload: WorkbenchWorkspaceOutputCreatePayload
    ) -> WorkbenchWorkspaceOutputRecord: ...

    def mark_task_completed(
        self,
        task_id: str,
        *,
        updated_at: str,
        result_text: str,
        result_citations: list[dict[str, object]] | None = None,
        workspace_output_count: int | None = None,
    ) -> None: ...

    def mark_task_failed(
        self, task_id: str, *, updated_at: str, error_detail: str
    ) -> None: ...

    def get_task(self, task_id: str) -> WorkbenchTaskRecord | None: ...

    def list_task_ids_by_status(self, statuses: Iterable[str]) -> list[str]: ...

    def list_task_events(self, task_id: str) -> list[WorkbenchTaskEventRecord]: ...

    def list_workspace_outputs(
        self, task_id: str
    ) -> list[WorkbenchWorkspaceOutputRecord]: ...

    def get_workspace_output(
        self, output_id: str
    ) -> WorkbenchWorkspaceOutputRecord | None: ...

    def list_workspace_outputs_for_session(
        self, session_id: str
    ) -> list[WorkbenchWorkspaceOutputRecord]: ...

    def list_workspace_outputs_for_project(
        self, project_id: str
    ) -> list[WorkbenchWorkspaceOutputRecord]: ...

    def replace_workspace_output_metadata(
        self,
        output_id: str,
        *,
        metadata: dict[str, object],
        updated_at: str,
    ) -> None: ...

    def append_task_event(
        self,
        task_id: str,
        *,
        event_type: str,
        created_at: str,
        status: str | None,
        message: str | None,
        metadata: dict[str, object] | None,
    ) -> None: ...


class SQLiteWorkbenchTaskRepository:
    """SQLite-backed implementation of WorkbenchTaskRepository."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def create_task(self, payload: WorkbenchTaskCreatePayload) -> WorkbenchTaskRecord:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
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
                        json.dumps(payload.knowledge_document_ids, ensure_ascii=False),
                        json.dumps(payload.connector_ids, ensure_ascii=False),
                        json.dumps(payload.source_ids, ensure_ascii=False),
                        payload.error_detail,
                        None,
                        None,
                        payload.created_at,
                        payload.updated_at,
                        json.dumps(payload.auth_scopes or [], ensure_ascii=False),
                        payload.credential_id,
                        payload.auth_mode,
                        payload.owner_id,
                        payload.tenant_id,
                        payload.principal_id,
                    ),
                )
                self._append_event(
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
                conn.commit()
        except Exception as exc:
            _raise_write_error("workbench_task_create", exc)

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
                current = self._fetch_task_row(conn, task_id)
                if current is None:
                    conn.rollback()
                    return None
                cursor = conn.execute(
                    """
                    UPDATE workbench_tasks
                    SET status = 'running', updated_at = ?
                    WHERE id = ? AND status = 'queued'
                    """,
                    (updated_at, task_id),
                )
                if cursor.rowcount == 0:
                    conn.rollback()
                    return None
                self._append_event(
                    conn,
                    task_id=task_id,
                    event_type="task.started",
                    created_at=updated_at,
                    status="running",
                    message="Task execution started.",
                    metadata={"task_kind": str(current["task_kind"])},
                )
                conn.commit()
        except Exception as exc:
            _raise_write_error("workbench_task_claim", exc)
        return self.get_task(task_id)

    def create_workspace_output(
        self, payload: WorkbenchWorkspaceOutputCreatePayload
    ) -> WorkbenchWorkspaceOutputRecord:
        metadata_json = None
        if payload.metadata:
            metadata_json = json.dumps(
                payload.metadata, ensure_ascii=False, sort_keys=True
            )
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
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
                self._append_event(
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
                conn.commit()
        except Exception as exc:
            _raise_write_error("workbench_workspace_output_create", exc)

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
                citations_json = None
                if result_citations:
                    citations_json = json.dumps(
                        result_citations, ensure_ascii=False, sort_keys=True
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
                    conn.rollback()
                    return
                self._append_event(
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
                conn.commit()
        except Exception as exc:
            _raise_write_error("workbench_task_complete", exc)

    def mark_task_failed(
        self, task_id: str, *, updated_at: str, error_detail: str
    ) -> None:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
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
                    conn.rollback()
                    return
                self._append_event(
                    conn,
                    task_id=task_id,
                    event_type="task.failed",
                    created_at=updated_at,
                    status="failed",
                    message=error_detail,
                    metadata={},
                )
                conn.commit()
        except Exception as exc:
            _raise_write_error("workbench_task_fail", exc)

    def get_task(self, task_id: str) -> WorkbenchTaskRecord | None:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = self._fetch_task_row(conn, task_id)
        except Exception as exc:
            _raise_read_error("workbench_task_get", exc)

        if row is None:
            return None

        return WorkbenchTaskRecord(
            id=str(row["id"]),
            task_kind=str(row["task_kind"]),
            status=str(row["status"]),
            prompt=str(row["prompt"]),
            session_id=(
                str(row["session_id"]) if row["session_id"] is not None else None
            ),
            project_id=(
                str(row["project_id"]) if row["project_id"] is not None else None
            ),
            knowledge_document_ids=_decode_string_list(row["knowledge_document_ids"]),
            connector_ids=_decode_string_list(row["connector_ids"]),
            source_ids=_decode_string_list(row["source_ids"]),
            error_detail=(
                str(row["error_detail"]) if row["error_detail"] is not None else None
            ),
            result_text=(
                str(row["result_text"]) if row["result_text"] is not None else None
            ),
            result_citations=_decode_object_list(row["result_citations_json"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            auth_scopes=_decode_string_list(row["auth_scopes_json"]),
            credential_id=str(row["credential_id"] or ""),
            auth_mode=str(row["auth_mode"] or ""),
            owner_id=str(row["owner_id"] or ""),
            tenant_id=str(row["tenant_id"] or "tenant:default"),
            principal_id=str(row["principal_id"] or ""),
        )

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
            _raise_read_error("workbench_task_ids_list", exc)
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
            _raise_read_error("workbench_task_events_list", exc)
        return [self._row_to_event(row) for row in rows]

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
            _raise_read_error("workbench_workspace_outputs_list", exc)
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
            _raise_read_error("workbench_workspace_output_get", exc)
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
        metadata_json = json.dumps(metadata, ensure_ascii=False, sort_keys=True)
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                cursor = conn.execute(
                    """
                    UPDATE workbench_workspace_outputs
                    SET metadata_json = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (metadata_json, updated_at, output_id),
                )
                if cursor.rowcount == 0:
                    conn.rollback()
                    return
                conn.commit()
        except Exception as exc:
            _raise_write_error("workbench_workspace_output_metadata_replace", exc)

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
                self._append_event(
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
            _raise_write_error("workbench_task_event_append", exc)

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
        seq = conn.execute(
            "SELECT COALESCE(MAX(seq), 0) + 1 FROM workbench_task_events WHERE task_id = ?",
            (task_id,),
        ).fetchone()[0]
        metadata_json = None
        if metadata:
            metadata_json = json.dumps(metadata, ensure_ascii=False, sort_keys=True)
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
            (task_id, int(seq), event_type, created_at, status, message, metadata_json),
        )

    def _row_to_event(self, row: sqlite3.Row) -> WorkbenchTaskEventRecord:
        metadata: dict[str, object] | None = None
        metadata_raw = row["metadata_json"]
        if isinstance(metadata_raw, str) and metadata_raw.strip():
            try:
                parsed = json.loads(metadata_raw)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict):
                metadata = parsed
        return WorkbenchTaskEventRecord(
            task_id=str(row["task_id"]),
            sequence=int(row["seq"]),
            event_type=str(row["event_type"]),
            created_at=str(row["created_at"]),
            status=str(row["status"]) if row["status"] is not None else None,
            message=str(row["message"]) if row["message"] is not None else None,
            metadata=metadata,
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
            _raise_read_error(operation, exc)
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
            metadata=_decode_object(row["metadata_json"]),
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
