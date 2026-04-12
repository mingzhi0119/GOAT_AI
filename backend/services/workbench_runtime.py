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
from backend.services.sqlite_persistence_utils import raise_write_error


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
