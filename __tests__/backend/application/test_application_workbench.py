from __future__ import annotations

import unittest
from pathlib import Path

from backend.application.exceptions import (
    WorkbenchPermissionDeniedError,
    WorkbenchSourceValidationError,
    WorkbenchTaskConflictError,
    WorkbenchTaskNotFoundError,
    WorkbenchWorkspaceOutputNotFoundError,
)
from backend.application.workbench import (
    cancel_workbench_task,
    create_and_dispatch_workbench_task,
    create_workbench_task,
    export_workbench_workspace_output,
    get_workbench_task,
    get_workbench_workspace_output,
    list_workbench_workspace_outputs,
    retry_workbench_task,
)
from backend.domain.authz_types import AuthorizationContext
from backend.domain.authorization import AuthorizationDecision, PrincipalId, TenantId
from backend.models.workbench import WorkbenchTaskRequest
from backend.services.workbench_runtime import (
    WorkbenchTaskCreatePayload,
    WorkbenchTaskRecord,
    WorkbenchWorkspaceOutputRecord,
)
from backend.services.workbench_source_registry import WorkbenchSourceDescriptor
from goat_ai.config.settings import Settings
from backend.services.artifact_service import PersistedArtifactRecord


def _settings() -> Settings:
    return Settings(
        ollama_base_url="http://127.0.0.1:11434",
        generate_timeout=120,
        max_upload_mb=20,
        max_upload_bytes=20 * 1024 * 1024,
        max_dataframe_rows=50000,
        use_chat_api=True,
        system_prompt="test",
        app_root=Path("."),
        logo_svg=Path("logo.svg"),
        log_db_path=Path("chat_logs.db"),
        data_dir=Path("data"),
        feature_agent_workbench_enabled=True,
        require_session_owner=True,
    )


def _auth_context(owner_id: str = "owner-1") -> AuthorizationContext:
    return AuthorizationContext(
        principal_id=PrincipalId("principal-1"),
        tenant_id=TenantId("tenant-1"),
        scopes=frozenset(
            {
                "workbench:read",
                "workbench:write",
                "workbench:export",
                "knowledge:read",
                "artifact:write",
                "history:read",
                "history:write",
            }
        ),
        credential_id="cred-1",
        legacy_owner_id=owner_id,
        auth_mode="api_key",
    )


class _FakeRepository:
    def __init__(self) -> None:
        self.created_payload: WorkbenchTaskCreatePayload | None = None
        self.created_payloads: list[WorkbenchTaskCreatePayload] = []
        self.task: WorkbenchTaskRecord | None = None
        self.tasks: dict[str, WorkbenchTaskRecord] = {}
        self.workspace_outputs: list[WorkbenchWorkspaceOutputRecord] = []
        self.appended_events: list[dict[str, object]] = []

    def create_task(self, payload: WorkbenchTaskCreatePayload) -> WorkbenchTaskRecord:
        self.created_payload = payload
        self.created_payloads.append(payload)
        record = WorkbenchTaskRecord(
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
            auth_scopes=list(payload.auth_scopes or []),
            credential_id=payload.credential_id,
            auth_mode=payload.auth_mode,
            owner_id=payload.owner_id,
            tenant_id=payload.tenant_id,
            principal_id=payload.principal_id,
        )
        self.task = record
        self.tasks[record.id] = record
        return record

    def mark_task_cancelled(
        self, task_id: str, *, updated_at: str, error_detail: str
    ) -> None:
        task = self.tasks.get(task_id)
        if task is None or task.status != "queued":
            return
        updated = WorkbenchTaskRecord(
            **{
                **task.__dict__,
                "status": "cancelled",
                "updated_at": updated_at,
                "error_detail": error_detail,
                "result_text": None,
                "result_citations": None,
            }
        )
        self.tasks[task_id] = updated
        self.task = updated
        self.append_task_event(
            task_id,
            event_type="task.cancelled",
            created_at=updated_at,
            status="cancelled",
            message=error_detail,
            metadata={},
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
        self.appended_events.append(
            {
                "task_id": task_id,
                "event_type": event_type,
                "created_at": created_at,
                "status": status,
                "message": message,
                "metadata": metadata,
            }
        )

    def get_task(self, task_id: str) -> WorkbenchTaskRecord | None:
        return self.tasks.get(task_id)

    def list_task_events(self, task_id: str) -> list[object]:
        _ = task_id
        return []

    def list_workspace_outputs(
        self, task_id: str
    ) -> list[WorkbenchWorkspaceOutputRecord]:
        return [
            output for output in self.workspace_outputs if output.task_id == task_id
        ]

    def get_workspace_output(
        self, output_id: str
    ) -> WorkbenchWorkspaceOutputRecord | None:
        for output in self.workspace_outputs:
            if output.id == output_id:
                return output
        return None

    def list_workspace_outputs_for_session(
        self, session_id: str
    ) -> list[WorkbenchWorkspaceOutputRecord]:
        return [
            output
            for output in self.workspace_outputs
            if output.session_id == session_id
        ]

    def list_workspace_outputs_for_project(
        self, project_id: str
    ) -> list[WorkbenchWorkspaceOutputRecord]:
        return [
            output
            for output in self.workspace_outputs
            if output.project_id == project_id
        ]


class _FakeDispatcher:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def dispatch_task(self, *, task_id: str, request_id: str = "") -> None:
        self.calls.append((task_id, request_id))


class _FakeSessionRepository:
    def __init__(self) -> None:
        self.artifacts: list[PersistedArtifactRecord] = []

    def create_chat_artifact(self, record: PersistedArtifactRecord) -> None:
        self.artifacts.append(record)


def _seed_task(
    repository: _FakeRepository,
    *,
    task_id: str = "wb-seeded",
    status: str = "queued",
    task_kind: str = "plan",
    prompt: str = "Draft a plan",
    session_id: str | None = None,
    project_id: str | None = None,
    knowledge_document_ids: list[str] | None = None,
    connector_ids: list[str] | None = None,
    source_ids: list[str] | None = None,
    owner_id: str = "owner-1",
    tenant_id: str = "tenant-1",
    principal_id: str = "principal-1",
    auth_scopes: list[str] | None = None,
    credential_id: str = "cred-1",
    auth_mode: str = "api_key",
) -> WorkbenchTaskRecord:
    task = WorkbenchTaskRecord(
        id=task_id,
        task_kind=task_kind,
        status=status,
        prompt=prompt,
        session_id=session_id,
        project_id=project_id,
        knowledge_document_ids=list(knowledge_document_ids or []),
        connector_ids=list(connector_ids or []),
        source_ids=list(source_ids or []),
        created_at="2026-04-11T00:00:00+00:00",
        updated_at="2026-04-11T00:00:00+00:00",
        error_detail="Task failed." if status == "failed" else None,
        result_text="## Goal\n- done" if status == "completed" else None,
        auth_scopes=list(auth_scopes or ["knowledge:read"]),
        credential_id=credential_id,
        auth_mode=auth_mode,
        owner_id=owner_id,
        tenant_id=tenant_id,
        principal_id=principal_id,
    )
    repository.tasks[task.id] = task
    repository.task = task
    return task


class ApplicationWorkbenchTests(unittest.TestCase):
    def test_create_workbench_task_requires_workbench_write_scope(self) -> None:
        repository = _FakeRepository()
        request = WorkbenchTaskRequest(
            task_kind="plan",
            prompt="Plan the migration",
        )

        with self.assertRaises(WorkbenchPermissionDeniedError):
            create_workbench_task(
                request=request,
                repository=repository,
                settings=_settings(),
                auth_context=AuthorizationContext(
                    principal_id=PrincipalId("principal-1"),
                    tenant_id=TenantId("tenant-1"),
                    scopes=frozenset({"workbench:read"}),
                    credential_id="cred-limited",
                    legacy_owner_id="owner-1",
                    auth_mode="api_key",
                ),
            )

    def test_create_browse_task_requires_runtime_ready_source(self) -> None:
        repository = _FakeRepository()
        request = WorkbenchTaskRequest(
            task_kind="browse",
            prompt="Find evidence",
            source_ids=["web"],
        )

        from unittest.mock import patch

        with patch(
            "backend.application.workbench_task_lifecycle.resolve_requested_sources",
            return_value=[
                WorkbenchSourceDescriptor(
                    source_id="web",
                    display_name="Public Web",
                    kind="builtin",
                    scope_kind="global",
                    capabilities=("search",),
                    task_kinds=("browse",),
                    read_only=True,
                    runtime_ready=False,
                    deny_reason="not_implemented",
                    description="web",
                )
            ],
        ):
            with self.assertRaises(WorkbenchSourceValidationError):
                create_workbench_task(
                    request=request,
                    repository=repository,
                    settings=_settings(),
                    auth_context=_auth_context(),
                )

    def test_create_workbench_task_rejects_sources_without_task_kind_support(
        self,
    ) -> None:
        repository = _FakeRepository()
        request = WorkbenchTaskRequest(
            task_kind="plan",
            prompt="Plan the migration",
            source_ids=["web"],
        )

        from unittest.mock import patch

        with patch(
            "backend.application.workbench_task_lifecycle.resolve_requested_sources",
            return_value=[
                WorkbenchSourceDescriptor(
                    source_id="web",
                    display_name="Public Web",
                    kind="builtin",
                    scope_kind="global",
                    capabilities=("search",),
                    task_kinds=("browse",),
                    read_only=True,
                    runtime_ready=True,
                    deny_reason=None,
                    description="web",
                )
            ],
        ):
            with self.assertRaisesRegex(
                WorkbenchSourceValidationError,
                "do not support task kind 'plan': web",
            ):
                create_workbench_task(
                    request=request,
                    repository=repository,
                    settings=_settings(),
                    auth_context=_auth_context(),
                )

    def test_create_deep_research_defaults_to_web_when_no_sources_are_provided(
        self,
    ) -> None:
        repository = _FakeRepository()
        request = WorkbenchTaskRequest(
            task_kind="deep_research",
            prompt="Investigate recent product launches",
        )

        from unittest.mock import patch

        with patch(
            "backend.application.workbench_task_lifecycle.resolve_requested_sources",
            return_value=[
                WorkbenchSourceDescriptor(
                    source_id="web",
                    display_name="Public Web",
                    kind="builtin",
                    scope_kind="global",
                    capabilities=("search", "citations"),
                    task_kinds=("browse", "deep_research"),
                    read_only=True,
                    runtime_ready=True,
                    deny_reason=None,
                    description="web",
                )
            ],
        ):
            accepted = create_workbench_task(
                request=request,
                repository=repository,
                settings=_settings(),
                auth_context=_auth_context(),
            )

        assert repository.created_payload is not None
        self.assertEqual(["web"], repository.created_payload.source_ids)
        self.assertEqual("deep_research", accepted.task_kind)

    def test_create_and_dispatch_workbench_task_preserves_request_context(self) -> None:
        repository = _FakeRepository()
        dispatcher = _FakeDispatcher()
        request = WorkbenchTaskRequest(
            task_kind="plan",
            prompt="Plan the migration",
            knowledge_document_ids=["doc-1"],
        )

        from unittest.mock import patch

        with patch(
            "backend.application.workbench_task_lifecycle.resolve_requested_sources",
            return_value=[
                WorkbenchSourceDescriptor(
                    source_id="knowledge",
                    display_name="Knowledge Base",
                    kind="knowledge",
                    scope_kind="knowledge_documents",
                    capabilities=("search",),
                    task_kinds=("plan",),
                    read_only=True,
                    runtime_ready=True,
                    deny_reason=None,
                    description="knowledge",
                    required_scope="knowledge:read",
                )
            ],
        ):
            accepted = create_and_dispatch_workbench_task(
                request=request,
                repository=repository,
                dispatcher=dispatcher,
                settings=_settings(),
                auth_context=_auth_context(),
                request_id="req-123",
            )

        assert repository.created_payload is not None
        self.assertEqual(["knowledge"], repository.created_payload.source_ids)
        self.assertEqual(
            ("{}".format(accepted.task_id), "req-123"), dispatcher.calls[0]
        )

    def test_get_workbench_task_conceals_unauthorized_records(self) -> None:
        repository = _FakeRepository()
        _seed_task(repository, task_id="wb-1", status="queued", prompt="Plan")

        from unittest.mock import patch

        with patch(
            "backend.application.workbench_shared.authorize_workbench_task_read",
            return_value=AuthorizationDecision(
                allowed=False,
                reason_code="owner_mismatch",
                conceal_existence=True,
            ),
        ):
            with self.assertRaises(WorkbenchTaskNotFoundError):
                get_workbench_task(
                    task_id="wb-1",
                    repository=repository,
                    settings=_settings(),
                    auth_context=_auth_context(owner_id="other-owner"),
                )

    def test_get_workbench_task_includes_workspace_outputs(self) -> None:
        repository = _FakeRepository()
        _seed_task(
            repository,
            task_id="wb-2",
            task_kind="canvas",
            status="completed",
            prompt="Draft",
            session_id="session-1",
        )
        repository.tasks["wb-2"] = WorkbenchTaskRecord(
            **{
                **repository.tasks["wb-2"].__dict__,
                "updated_at": "2026-04-11T00:00:02+00:00",
                "result_text": "# Draft\n\nBody",
            }
        )
        repository.workspace_outputs = [
            WorkbenchWorkspaceOutputRecord(
                id="wbo-1",
                task_id="wb-2",
                output_kind="canvas_document",
                title="Draft",
                content_format="markdown",
                content_text="# Draft\n\nBody",
                created_at="2026-04-11T00:00:01+00:00",
                updated_at="2026-04-11T00:00:02+00:00",
                metadata={"editable": True},
                owner_id="owner-1",
                tenant_id="tenant-1",
                principal_id="principal-1",
            )
        ]

        from unittest.mock import patch

        with patch(
            "backend.application.workbench_shared.authorize_workbench_task_read",
            return_value=AuthorizationDecision(
                allowed=True,
                reason_code="allowed",
                conceal_existence=False,
            ),
        ):
            response = get_workbench_task(
                task_id="wb-2",
                repository=repository,
                settings=_settings(),
                auth_context=_auth_context(),
            )

        self.assertEqual("completed", response.status)
        self.assertEqual(1, len(response.workspace_outputs))
        self.assertEqual("wbo-1", response.workspace_outputs[0].output_id)
        self.assertEqual("canvas_document", response.workspace_outputs[0].output_kind)

    def test_get_workbench_task_filters_hidden_workspace_outputs(self) -> None:
        repository = _FakeRepository()
        _seed_task(
            repository,
            task_id="wb-2",
            task_kind="canvas",
            status="completed",
            prompt="Draft",
            session_id="session-1",
        )
        repository.workspace_outputs = [
            WorkbenchWorkspaceOutputRecord(
                id="wbo-visible",
                task_id="wb-2",
                output_kind="canvas_document",
                title="Draft",
                content_format="markdown",
                content_text="# Draft\n\nVisible",
                created_at="2026-04-11T00:00:01+00:00",
                updated_at="2026-04-11T00:00:02+00:00",
                owner_id="owner-1",
                tenant_id="tenant-1",
                principal_id="principal-1",
            ),
            WorkbenchWorkspaceOutputRecord(
                id="wbo-hidden",
                task_id="wb-2",
                output_kind="canvas_document",
                title="Hidden",
                content_format="markdown",
                content_text="# Hidden",
                created_at="2026-04-11T00:00:03+00:00",
                updated_at="2026-04-11T00:00:04+00:00",
                owner_id="other-owner",
                tenant_id="tenant-1",
                principal_id="principal-1",
            ),
        ]

        from unittest.mock import patch

        with patch(
            "backend.application.workbench_shared.authorize_workbench_task_read",
            return_value=AuthorizationDecision(
                allowed=True,
                reason_code="allowed",
                conceal_existence=False,
            ),
        ):
            response = get_workbench_task(
                task_id="wb-2",
                repository=repository,
                settings=_settings(),
                auth_context=_auth_context(),
            )

        self.assertEqual(
            ["wbo-visible"], [item.output_id for item in response.workspace_outputs]
        )

    def test_cancel_workbench_task_marks_queued_task_cancelled(self) -> None:
        repository = _FakeRepository()
        _seed_task(repository, status="queued")

        response = cancel_workbench_task(
            task_id="wb-seeded",
            repository=repository,
            settings=_settings(),
            auth_context=_auth_context(),
        )

        self.assertEqual("cancelled", response.status)
        self.assertEqual("Task cancelled before execution.", response.error_detail)
        self.assertEqual("task.cancelled", repository.appended_events[-1]["event_type"])

    def test_cancel_workbench_task_filters_hidden_workspace_outputs(self) -> None:
        repository = _FakeRepository()
        _seed_task(
            repository, task_id="wb-visible", status="queued", session_id="session-1"
        )
        repository.workspace_outputs = [
            WorkbenchWorkspaceOutputRecord(
                id="wbo-visible",
                task_id="wb-visible",
                output_kind="canvas_document",
                title="Visible",
                content_format="markdown",
                content_text="# Visible",
                created_at="2026-04-11T00:00:01+00:00",
                updated_at="2026-04-11T00:00:02+00:00",
                owner_id="owner-1",
                tenant_id="tenant-1",
                principal_id="principal-1",
            ),
            WorkbenchWorkspaceOutputRecord(
                id="wbo-hidden",
                task_id="wb-visible",
                output_kind="canvas_document",
                title="Hidden",
                content_format="markdown",
                content_text="# Hidden",
                created_at="2026-04-11T00:00:03+00:00",
                updated_at="2026-04-11T00:00:04+00:00",
                owner_id="other-owner",
                tenant_id="tenant-1",
                principal_id="principal-1",
            ),
        ]

        response = cancel_workbench_task(
            task_id="wb-visible",
            repository=repository,
            settings=_settings(),
            auth_context=_auth_context(),
        )

        self.assertEqual(
            ["wbo-visible"], [item.output_id for item in response.workspace_outputs]
        )

    def test_cancel_workbench_task_rejects_non_queued_state(self) -> None:
        repository = _FakeRepository()
        _seed_task(repository, status="running")

        with self.assertRaises(WorkbenchTaskConflictError):
            cancel_workbench_task(
                task_id="wb-seeded",
                repository=repository,
                settings=_settings(),
                auth_context=_auth_context(),
            )

    def test_retry_workbench_task_reuses_request_shape_but_refreshes_auth_snapshot(
        self,
    ) -> None:
        repository = _FakeRepository()
        dispatcher = _FakeDispatcher()
        seeded = _seed_task(
            repository,
            task_id="wb-original",
            status="completed",
            task_kind="deep_research",
            prompt="Investigate launches",
            session_id="session-1",
            project_id="project-1",
            knowledge_document_ids=["doc-1"],
            connector_ids=["connector-a"],
            source_ids=["web", "knowledge"],
            owner_id="owner-original",
            tenant_id="tenant-original",
            principal_id="principal-original",
            auth_scopes=["workbench:read", "workbench:write", "knowledge:read"],
            credential_id="cred-original",
            auth_mode="scoped_key",
        )

        from unittest.mock import patch

        with patch(
            "backend.application.workbench_task_lifecycle.resolve_requested_sources",
            return_value=[
                WorkbenchSourceDescriptor(
                    source_id="web",
                    display_name="Public Web",
                    kind="builtin",
                    scope_kind="global",
                    capabilities=("search",),
                    task_kinds=("deep_research",),
                    read_only=True,
                    runtime_ready=True,
                    deny_reason=None,
                    description="web",
                ),
                WorkbenchSourceDescriptor(
                    source_id="knowledge",
                    display_name="Knowledge Base",
                    kind="knowledge",
                    scope_kind="knowledge_documents",
                    capabilities=("search",),
                    task_kinds=("deep_research",),
                    read_only=True,
                    runtime_ready=True,
                    deny_reason=None,
                    description="knowledge",
                    required_scope="knowledge:read",
                ),
            ],
        ):
            accepted = retry_workbench_task(
                task_id=seeded.id,
                repository=repository,
                dispatcher=dispatcher,
                settings=_settings(),
                auth_context=AuthorizationContext(
                    principal_id=PrincipalId("principal-original"),
                    tenant_id=TenantId("tenant-original"),
                    scopes=frozenset(
                        {
                            "workbench:read",
                            "workbench:write",
                            "knowledge:read",
                        }
                    ),
                    credential_id="cred-current",
                    legacy_owner_id="owner-original",
                    auth_mode="api_key",
                ),
                request_id="req-456",
            )

        self.assertEqual("queued", accepted.status)
        self.assertEqual(1, len(dispatcher.calls))
        self.assertEqual((accepted.task_id, "req-456"), dispatcher.calls[0])
        retried_payload = repository.created_payloads[-1]
        self.assertNotEqual(seeded.id, retried_payload.task_id)
        self.assertEqual("deep_research", retried_payload.task_kind)
        self.assertEqual("Investigate launches", retried_payload.prompt)
        self.assertEqual("session-1", retried_payload.session_id)
        self.assertEqual("project-1", retried_payload.project_id)
        self.assertEqual(["doc-1"], retried_payload.knowledge_document_ids)
        self.assertEqual(["connector-a"], retried_payload.connector_ids)
        self.assertEqual(["web", "knowledge"], retried_payload.source_ids)
        self.assertEqual("owner-original", retried_payload.owner_id)
        self.assertEqual("tenant-original", retried_payload.tenant_id)
        self.assertEqual("principal-original", retried_payload.principal_id)
        self.assertEqual(
            ["knowledge:read", "workbench:read", "workbench:write"],
            retried_payload.auth_scopes,
        )
        self.assertEqual("cred-current", retried_payload.credential_id)
        self.assertEqual("api_key", retried_payload.auth_mode)
        self.assertEqual(
            "task.retry_requested",
            repository.appended_events[-2]["event_type"],
        )
        self.assertEqual(
            accepted.task_id,
            repository.appended_events[-2]["metadata"]["retry_task_id"],
        )
        self.assertEqual(
            "task.retry_created",
            repository.appended_events[-1]["event_type"],
        )
        self.assertEqual(
            seeded.id,
            repository.appended_events[-1]["metadata"]["source_task_id"],
        )

    def test_retry_workbench_task_rejects_source_scope_regressions(self) -> None:
        repository = _FakeRepository()
        _seed_task(
            repository,
            task_id="wb-original",
            status="completed",
            task_kind="deep_research",
            source_ids=["knowledge"],
        )

        with self.assertRaises(WorkbenchPermissionDeniedError):
            retry_workbench_task(
                task_id="wb-original",
                repository=repository,
                dispatcher=_FakeDispatcher(),
                settings=_settings(),
                auth_context=AuthorizationContext(
                    principal_id=PrincipalId("principal-1"),
                    tenant_id=TenantId("tenant-1"),
                    scopes=frozenset({"workbench:read", "workbench:write"}),
                    credential_id="cred-limited",
                    legacy_owner_id="owner-1",
                    auth_mode="api_key",
                ),
            )

    def test_retry_workbench_task_rejects_source_capability_regressions(self) -> None:
        repository = _FakeRepository()
        _seed_task(
            repository,
            task_id="wb-original",
            status="completed",
            task_kind="browse",
            source_ids=["web"],
        )

        from unittest.mock import patch

        with patch(
            "backend.application.workbench_task_lifecycle.resolve_requested_sources",
            return_value=[
                WorkbenchSourceDescriptor(
                    source_id="web",
                    display_name="Public Web",
                    kind="builtin",
                    scope_kind="global",
                    capabilities=("search",),
                    task_kinds=("deep_research",),
                    read_only=True,
                    runtime_ready=True,
                    deny_reason=None,
                    description="web",
                )
            ],
        ):
            with self.assertRaisesRegex(
                WorkbenchSourceValidationError,
                "do not support task kind 'browse': web",
            ):
                retry_workbench_task(
                    task_id="wb-original",
                    repository=repository,
                    dispatcher=_FakeDispatcher(),
                    settings=_settings(),
                    auth_context=_auth_context(),
                )

    def test_retry_workbench_task_rejects_non_terminal_state(self) -> None:
        repository = _FakeRepository()
        _seed_task(repository, status="running")

        with self.assertRaises(WorkbenchTaskConflictError):
            retry_workbench_task(
                task_id="wb-seeded",
                repository=repository,
                dispatcher=_FakeDispatcher(),
                settings=_settings(),
                auth_context=_auth_context(),
            )

    def test_create_workbench_task_rejects_project_memory_without_project_id(
        self,
    ) -> None:
        repository = _FakeRepository()
        project_memory_source = WorkbenchSourceDescriptor(
            source_id="project_memory",
            display_name="Project Memory",
            kind="project_memory",
            scope_kind="project_scope",
            capabilities=("search", "citations"),
            task_kinds=("browse", "deep_research"),
            read_only=True,
            runtime_ready=True,
            deny_reason=None,
            description="project memory",
            requires_project_id=True,
        )

        from unittest.mock import patch

        with patch(
            "backend.application.workbench_task_lifecycle.resolve_requested_sources",
            return_value=[project_memory_source],
        ):
            with self.assertRaisesRegex(
                WorkbenchSourceValidationError,
                "require project_id",
            ):
                create_workbench_task(
                    request=WorkbenchTaskRequest(
                        task_kind="browse",
                        prompt="Search project memory",
                        source_ids=["project_memory"],
                    ),
                    repository=repository,
                    settings=_settings(),
                    auth_context=_auth_context(),
                )

    def test_get_workbench_workspace_output_conceals_unauthorized_records(self) -> None:
        repository = _FakeRepository()
        repository.workspace_outputs = [
            WorkbenchWorkspaceOutputRecord(
                id="wbo-1",
                task_id="wb-2",
                output_kind="canvas_document",
                title="Draft",
                content_format="markdown",
                content_text="# Draft",
                created_at="2026-04-11T00:00:01+00:00",
                updated_at="2026-04-11T00:00:02+00:00",
                owner_id="owner-1",
                tenant_id="tenant-1",
                principal_id="principal-1",
            )
        ]

        with self.assertRaises(WorkbenchWorkspaceOutputNotFoundError):
            get_workbench_workspace_output(
                output_id="wbo-1",
                repository=repository,
                settings=_settings(),
                auth_context=_auth_context(owner_id="other-owner"),
            )

    def test_export_workbench_workspace_output_requires_export_scope(self) -> None:
        repository = _FakeRepository()
        repository.workspace_outputs = [
            WorkbenchWorkspaceOutputRecord(
                id="wbo-1",
                task_id="wb-2",
                output_kind="canvas_document",
                title="Draft",
                content_format="markdown",
                content_text="# Draft",
                created_at="2026-04-11T00:00:01+00:00",
                updated_at="2026-04-11T00:00:02+00:00",
                owner_id="owner-1",
                tenant_id="tenant-1",
                principal_id="principal-1",
            )
        ]

        from backend.models.workbench import WorkbenchWorkspaceOutputExportRequest

        with self.assertRaises(WorkbenchPermissionDeniedError):
            export_workbench_workspace_output(
                output_id="wbo-1",
                request=WorkbenchWorkspaceOutputExportRequest(format="markdown"),
                task_repository=repository,
                session_repository=_FakeSessionRepository(),
                settings=_settings(),
                auth_context=AuthorizationContext(
                    principal_id=PrincipalId("principal-1"),
                    tenant_id=TenantId("tenant-1"),
                    scopes=frozenset({"workbench:read", "artifact:write"}),
                    credential_id="cred-limited",
                    legacy_owner_id="owner-1",
                    auth_mode="api_key",
                ),
            )

    def test_list_workbench_workspace_outputs_by_session_filters_visible_outputs(
        self,
    ) -> None:
        repository = _FakeRepository()
        repository.workspace_outputs = [
            WorkbenchWorkspaceOutputRecord(
                id="wbo-1",
                task_id="wb-2",
                output_kind="canvas_document",
                title="Draft",
                content_format="markdown",
                content_text="# Draft",
                created_at="2026-04-11T00:00:01+00:00",
                updated_at="2026-04-11T00:00:02+00:00",
                session_id="session-1",
                owner_id="owner-1",
                tenant_id="tenant-1",
                principal_id="principal-1",
            ),
            WorkbenchWorkspaceOutputRecord(
                id="wbo-2",
                task_id="wb-3",
                output_kind="canvas_document",
                title="Hidden",
                content_format="markdown",
                content_text="# Hidden",
                created_at="2026-04-11T00:00:03+00:00",
                updated_at="2026-04-11T00:00:04+00:00",
                session_id="session-1",
                owner_id="other-owner",
                tenant_id="tenant-1",
                principal_id="principal-1",
            ),
        ]

        response = list_workbench_workspace_outputs(
            repository=repository,
            settings=_settings(),
            auth_context=_auth_context(),
            session_id="session-1",
        )

        self.assertEqual(1, len(response.outputs))
        self.assertEqual("wbo-1", response.outputs[0].output_id)

    def test_export_workbench_workspace_output_registers_linked_artifact(self) -> None:
        repository = _FakeRepository()
        session_repository = _FakeSessionRepository()
        repository.workspace_outputs = [
            WorkbenchWorkspaceOutputRecord(
                id="wbo-1",
                task_id="wb-2",
                output_kind="canvas_document",
                title="Draft Canvas",
                content_format="markdown",
                content_text="# Draft Canvas\n\nBody",
                created_at="2026-04-11T00:00:01+00:00",
                updated_at="2026-04-11T00:00:02+00:00",
                session_id="session-1",
                owner_id="owner-1",
                tenant_id="tenant-1",
                principal_id="principal-1",
                metadata={"editable": True},
            )
        ]
        repository.appended_events: list[dict[str, object]] = []

        def _replace_workspace_output_metadata(
            output_id: str, *, metadata: dict[str, object], updated_at: str
        ) -> None:
            for index, output in enumerate(repository.workspace_outputs):
                if output.id != output_id:
                    continue
                repository.workspace_outputs[index] = WorkbenchWorkspaceOutputRecord(
                    **{
                        **output.__dict__,
                        "metadata": metadata,
                        "updated_at": updated_at,
                    }
                )

        def _append_task_event(
            task_id: str,
            *,
            event_type: str,
            created_at: str,
            status: str | None,
            message: str | None,
            metadata: dict[str, object] | None,
        ) -> None:
            repository.appended_events.append(
                {
                    "task_id": task_id,
                    "event_type": event_type,
                    "created_at": created_at,
                    "status": status,
                    "message": message,
                    "metadata": metadata,
                }
            )

        repository.replace_workspace_output_metadata = (
            _replace_workspace_output_metadata  # type: ignore[attr-defined]
        )
        repository.append_task_event = _append_task_event  # type: ignore[attr-defined]

        from backend.application.workbench import export_workbench_workspace_output
        from backend.models.workbench import WorkbenchWorkspaceOutputExportRequest

        artifact = export_workbench_workspace_output(
            output_id="wbo-1",
            request=WorkbenchWorkspaceOutputExportRequest(format="markdown"),
            task_repository=repository,
            session_repository=session_repository,
            settings=_settings(),
            auth_context=_auth_context(),
        )

        self.assertTrue(artifact.filename.endswith(".md"))
        self.assertEqual(1, len(session_repository.artifacts))
        refreshed = repository.workspace_outputs[0]
        self.assertEqual(
            artifact.artifact_id, refreshed.metadata["artifacts"][0]["artifact_id"]
        )
        self.assertEqual(
            "workspace_output.exported",
            repository.appended_events[0]["event_type"],
        )
