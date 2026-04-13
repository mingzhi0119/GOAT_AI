"""Typed runtime interfaces and SQLite adapter for workbench task persistence."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol

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
    decode_object,
    decode_object_list,
    decode_string_list,
    encode_json,
    raise_write_error,
)


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

    def mark_task_cancelled(
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
        from backend.services.workbench_task_store import SQLiteWorkbenchTaskStore
        from backend.services.workbench_workspace_output_store import (
            SQLiteWorkbenchWorkspaceOutputStore,
        )

        self._db_path = db_path
        self._task_store = SQLiteWorkbenchTaskStore(db_path)
        self._workspace_output_store = SQLiteWorkbenchWorkspaceOutputStore(db_path)

    def create_task(self, payload: WorkbenchTaskCreatePayload) -> WorkbenchTaskRecord:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                self._task_store.create_task_in_transaction(conn, payload)
                conn.commit()
        except Exception as exc:
            raise_write_error("workbench_task_create", exc)
        return self._task_store.get_task(payload.task_id) or WorkbenchTaskRecord(
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
                claimed = self._task_store.claim_task_for_execution_in_transaction(
                    conn, task_id, updated_at=updated_at
                )
                if not claimed:
                    conn.rollback()
                    return None
                conn.commit()
        except Exception as exc:
            raise_write_error("workbench_task_claim", exc)
        return self._task_store.get_task(task_id)

    def create_workspace_output(
        self, payload: WorkbenchWorkspaceOutputCreatePayload
    ) -> WorkbenchWorkspaceOutputRecord:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                self._workspace_output_store.create_workspace_output_in_transaction(
                    conn, payload
                )
                conn.commit()
        except Exception as exc:
            raise_write_error("workbench_workspace_output_create", exc)
        return self._workspace_output_store.get_workspace_output(
            payload.output_id
        ) or WorkbenchWorkspaceOutputRecord(
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
                updated = self._task_store.mark_task_completed_in_transaction(
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
                updated = self._task_store.mark_task_failed_in_transaction(
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
                updated = self._task_store.mark_task_cancelled_in_transaction(
                    conn, task_id, updated_at=updated_at, error_detail=error_detail
                )
                if not updated:
                    conn.rollback()
                    return
                conn.commit()
        except Exception as exc:
            raise_write_error("workbench_task_cancel", exc)

    def get_task(self, task_id: str) -> WorkbenchTaskRecord | None:
        return self._task_store.get_task(task_id)

    def list_task_ids_by_status(self, statuses: Iterable[str]) -> list[str]:
        return self._task_store.list_task_ids_by_status(statuses)

    def list_task_events(self, task_id: str) -> list[WorkbenchTaskEventRecord]:
        return self._task_store.list_task_events(task_id)

    def list_workspace_outputs(
        self, task_id: str
    ) -> list[WorkbenchWorkspaceOutputRecord]:
        return self._workspace_output_store.list_workspace_outputs(task_id)

    def get_workspace_output(
        self, output_id: str
    ) -> WorkbenchWorkspaceOutputRecord | None:
        return self._workspace_output_store.get_workspace_output(output_id)

    def list_workspace_outputs_for_session(
        self, session_id: str
    ) -> list[WorkbenchWorkspaceOutputRecord]:
        return self._workspace_output_store.list_workspace_outputs_for_session(
            session_id
        )

    def list_workspace_outputs_for_project(
        self, project_id: str
    ) -> list[WorkbenchWorkspaceOutputRecord]:
        return self._workspace_output_store.list_workspace_outputs_for_project(
            project_id
        )

    def replace_workspace_output_metadata(
        self,
        output_id: str,
        *,
        metadata: dict[str, object],
        updated_at: str,
    ) -> None:
        self._workspace_output_store.replace_workspace_output_metadata(
            output_id, metadata=metadata, updated_at=updated_at
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
                self._task_store.append_task_event_in_transaction(
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


class PostgresWorkbenchTaskRepository:
    """Postgres-backed implementation of WorkbenchTaskRepository."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def create_task(self, payload: WorkbenchTaskCreatePayload) -> WorkbenchTaskRecord:
        try:
            with postgres_connect(self._dsn) as conn:
                with conn.transaction():
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
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    self._append_task_event_in_transaction(
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
        except Exception as exc:
            raise PersistenceWriteError("Failed to workbench task create.") from exc
        return self.get_task(payload.task_id) or WorkbenchTaskRecord(
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
            with postgres_connect(self._dsn) as conn:
                with conn.transaction():
                    row = conn.execute(
                        "SELECT task_kind FROM workbench_tasks WHERE id = %s FOR UPDATE",
                        (task_id,),
                    ).fetchone()
                    if row is None:
                        return None
                    cursor = conn.execute(
                        """
                        UPDATE workbench_tasks
                        SET status = 'running', updated_at = %s
                        WHERE id = %s AND status = 'queued'
                        """,
                        (updated_at, task_id),
                    )
                    if cursor.rowcount == 0:
                        return None
                    self._append_task_event_in_transaction(
                        conn,
                        task_id=task_id,
                        event_type="task.started",
                        created_at=updated_at,
                        status="running",
                        message="Task execution started.",
                        metadata={"task_kind": str(row["task_kind"])},
                    )
        except Exception as exc:
            raise PersistenceWriteError("Failed to workbench task claim.") from exc
        return self.get_task(task_id)

    def create_workspace_output(
        self, payload: WorkbenchWorkspaceOutputCreatePayload
    ) -> WorkbenchWorkspaceOutputRecord:
        metadata_json = (
            encode_json(payload.metadata, sort_keys=True) if payload.metadata else None
        )
        try:
            with postgres_connect(self._dsn) as conn:
                with conn.transaction():
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
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    self._append_task_event_in_transaction(
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
        except Exception as exc:
            raise PersistenceWriteError(
                "Failed to workbench workspace output create."
            ) from exc
        return self.get_workspace_output(
            payload.output_id
        ) or WorkbenchWorkspaceOutputRecord(
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
        citations_json = (
            encode_json(result_citations, sort_keys=True)
            if result_citations is not None
            else None
        )
        try:
            with postgres_connect(self._dsn) as conn:
                with conn.transaction():
                    lock_parent_row(
                        conn,
                        table_name="workbench_tasks",
                        key_column="id",
                        key_value=task_id,
                    )
                    cursor = conn.execute(
                        """
                        UPDATE workbench_tasks
                        SET status = 'completed',
                            updated_at = %s,
                            error_detail = NULL,
                            result_text = %s,
                            result_citations_json = %s
                        WHERE id = %s AND status IN ('queued', 'running')
                        """,
                        (updated_at, result_text, citations_json, task_id),
                    )
                    if cursor.rowcount == 0:
                        return
                    self._append_task_event_in_transaction(
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
        except Exception as exc:
            raise PersistenceWriteError("Failed to workbench task complete.") from exc

    def mark_task_failed(
        self, task_id: str, *, updated_at: str, error_detail: str
    ) -> None:
        try:
            with postgres_connect(self._dsn) as conn:
                with conn.transaction():
                    lock_parent_row(
                        conn,
                        table_name="workbench_tasks",
                        key_column="id",
                        key_value=task_id,
                    )
                    cursor = conn.execute(
                        """
                        UPDATE workbench_tasks
                        SET status = 'failed',
                            updated_at = %s,
                            error_detail = %s,
                            result_text = NULL,
                            result_citations_json = NULL
                        WHERE id = %s AND status IN ('queued', 'running')
                        """,
                        (updated_at, error_detail, task_id),
                    )
                    if cursor.rowcount == 0:
                        return
                    self._append_task_event_in_transaction(
                        conn,
                        task_id=task_id,
                        event_type="task.failed",
                        created_at=updated_at,
                        status="failed",
                        message=error_detail,
                        metadata={},
                    )
        except Exception as exc:
            raise PersistenceWriteError("Failed to workbench task fail.") from exc

    def mark_task_cancelled(
        self, task_id: str, *, updated_at: str, error_detail: str
    ) -> None:
        try:
            with postgres_connect(self._dsn) as conn:
                with conn.transaction():
                    lock_parent_row(
                        conn,
                        table_name="workbench_tasks",
                        key_column="id",
                        key_value=task_id,
                    )
                    cursor = conn.execute(
                        """
                        UPDATE workbench_tasks
                        SET status = 'cancelled',
                            updated_at = %s,
                            error_detail = %s,
                            result_text = NULL,
                            result_citations_json = NULL
                        WHERE id = %s AND status = 'queued'
                        """,
                        (updated_at, error_detail, task_id),
                    )
                    if cursor.rowcount == 0:
                        return
                    self._append_task_event_in_transaction(
                        conn,
                        task_id=task_id,
                        event_type="task.cancelled",
                        created_at=updated_at,
                        status="cancelled",
                        message=error_detail,
                        metadata={},
                    )
        except Exception as exc:
            raise PersistenceWriteError("Failed to workbench task cancel.") from exc

    def get_task(self, task_id: str) -> WorkbenchTaskRecord | None:
        try:
            with postgres_connect(self._dsn) as conn:
                row = conn.execute(
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
                    WHERE id = %s
                    """,
                    (task_id,),
                ).fetchone()
        except Exception as exc:
            raise PersistenceReadError("Failed to workbench task get.") from exc
        if row is None:
            return None
        return self._row_to_task(row)

    def list_task_ids_by_status(self, statuses: Iterable[str]) -> list[str]:
        normalized = [str(status).strip() for status in statuses if str(status).strip()]
        if not normalized:
            return []
        try:
            with postgres_connect(self._dsn) as conn:
                rows = conn.execute(
                    """
                    SELECT id
                    FROM workbench_tasks
                    WHERE status = ANY(%s)
                    ORDER BY created_at ASC, id ASC
                    """,
                    (normalized,),
                ).fetchall()
        except Exception as exc:
            raise PersistenceReadError("Failed to workbench task ids list.") from exc
        return [str(row["id"]) for row in rows]

    def list_task_events(self, task_id: str) -> list[WorkbenchTaskEventRecord]:
        try:
            with postgres_connect(self._dsn) as conn:
                rows = conn.execute(
                    """
                    SELECT task_id, seq, event_type, created_at, status, message, metadata_json
                    FROM workbench_task_events
                    WHERE task_id = %s
                    ORDER BY seq ASC
                    """,
                    (task_id,),
                ).fetchall()
        except Exception as exc:
            raise PersistenceReadError("Failed to workbench task events list.") from exc
        return [
            WorkbenchTaskEventRecord(
                task_id=str(row["task_id"]),
                sequence=int(row["seq"]),
                event_type=str(row["event_type"]),
                created_at=str(row["created_at"]),
                status=str(row["status"]) if row["status"] is not None else None,
                message=str(row["message"]) if row["message"] is not None else None,
                metadata=decode_object(row["metadata_json"]),
            )
            for row in rows
        ]

    def list_workspace_outputs(
        self, task_id: str
    ) -> list[WorkbenchWorkspaceOutputRecord]:
        return self._list_workspace_outputs(
            where_clause="outputs.task_id = %s",
            params=(task_id,),
        )

    def get_workspace_output(
        self, output_id: str
    ) -> WorkbenchWorkspaceOutputRecord | None:
        rows = self._list_workspace_outputs(
            where_clause="outputs.id = %s",
            params=(output_id,),
        )
        return rows[0] if rows else None

    def list_workspace_outputs_for_session(
        self, session_id: str
    ) -> list[WorkbenchWorkspaceOutputRecord]:
        return self._list_workspace_outputs(
            where_clause="tasks.session_id = %s",
            params=(session_id,),
        )

    def list_workspace_outputs_for_project(
        self, project_id: str
    ) -> list[WorkbenchWorkspaceOutputRecord]:
        return self._list_workspace_outputs(
            where_clause="tasks.project_id = %s",
            params=(project_id,),
        )

    def replace_workspace_output_metadata(
        self,
        output_id: str,
        *,
        metadata: dict[str, object],
        updated_at: str,
    ) -> None:
        try:
            with postgres_connect(self._dsn) as conn:
                conn.execute(
                    """
                    UPDATE workbench_workspace_outputs
                    SET metadata_json = %s, updated_at = %s
                    WHERE id = %s
                    """,
                    (encode_json(metadata, sort_keys=True), updated_at, output_id),
                )
        except Exception as exc:
            raise PersistenceWriteError(
                "Failed to workbench workspace output metadata replace."
            ) from exc

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
            with postgres_connect(self._dsn) as conn:
                with conn.transaction():
                    self._append_task_event_in_transaction(
                        conn,
                        task_id=task_id,
                        event_type=event_type,
                        created_at=created_at,
                        status=status,
                        message=message,
                        metadata=metadata,
                    )
        except Exception as exc:
            raise PersistenceWriteError(
                "Failed to workbench task event append."
            ) from exc

    def _append_task_event_in_transaction(
        self,
        conn,
        *,
        task_id: str,
        event_type: str,
        created_at: str,
        status: str | None,
        message: str | None,
        metadata: dict[str, object] | None,
    ) -> None:
        lock_parent_row(
            conn,
            table_name="workbench_tasks",
            key_column="id",
            key_value=task_id,
        )
        seq = next_scoped_sequence(
            conn,
            table_name="workbench_task_events",
            scope_column="task_id",
            scope_value=task_id,
        )
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
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                task_id,
                seq,
                event_type,
                created_at,
                status,
                message,
                encode_json(metadata, sort_keys=True) if metadata is not None else None,
            ),
        )

    def _row_to_task(self, row) -> WorkbenchTaskRecord:
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

    def _list_workspace_outputs(
        self,
        *,
        where_clause: str,
        params: tuple[object, ...],
    ) -> list[WorkbenchWorkspaceOutputRecord]:
        try:
            with postgres_connect(self._dsn) as conn:
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
                    WHERE {where_clause}
                    ORDER BY outputs.created_at ASC, outputs.id ASC
                    """,
                    params,
                ).fetchall()
        except Exception as exc:
            raise PersistenceReadError(
                "Failed to workbench workspace outputs list."
            ) from exc
        return [
            WorkbenchWorkspaceOutputRecord(
                id=str(row["id"]),
                task_id=str(row["task_id"]),
                output_kind=str(row["output_kind"]),
                title=str(row["title"]),
                content_format=str(row["content_format"]),
                content_text=str(row["content_text"]),
                created_at=str(row["created_at"]),
                updated_at=str(row["updated_at"]),
                metadata=decode_object(row["metadata_json"]),
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
            for row in rows
        ]
