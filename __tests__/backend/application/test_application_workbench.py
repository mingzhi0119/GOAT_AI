from __future__ import annotations

import unittest
from pathlib import Path

from backend.application.exceptions import (
    WorkbenchSourceValidationError,
    WorkbenchTaskNotFoundError,
    WorkbenchWorkspaceOutputNotFoundError,
)
from backend.application.workbench import (
    create_and_dispatch_workbench_task,
    create_workbench_task,
    get_workbench_task,
    get_workbench_workspace_output,
    list_workbench_workspace_outputs,
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
        scopes=frozenset({"knowledge:read"}),
        credential_id="cred-1",
        legacy_owner_id=owner_id,
        auth_mode="api_key",
    )


class _FakeRepository:
    def __init__(self) -> None:
        self.created_payload: WorkbenchTaskCreatePayload | None = None
        self.task: WorkbenchTaskRecord | None = None
        self.workspace_outputs: list[WorkbenchWorkspaceOutputRecord] = []

    def create_task(self, payload: WorkbenchTaskCreatePayload) -> WorkbenchTaskRecord:
        self.created_payload = payload
        self.task = WorkbenchTaskRecord(
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
        return self.task

    def get_task(self, task_id: str) -> WorkbenchTaskRecord | None:
        if self.task and self.task.id == task_id:
            return self.task
        return None

    def list_task_events(self, task_id: str) -> list[object]:
        _ = task_id
        return []

    def list_workspace_outputs(
        self, task_id: str
    ) -> list[WorkbenchWorkspaceOutputRecord]:
        _ = task_id
        return list(self.workspace_outputs)

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


class ApplicationWorkbenchTests(unittest.TestCase):
    def test_create_browse_task_requires_runtime_ready_source(self) -> None:
        repository = _FakeRepository()
        request = WorkbenchTaskRequest(
            task_kind="browse",
            prompt="Find evidence",
            source_ids=["web"],
        )

        from unittest.mock import patch

        with patch(
            "backend.application.workbench.resolve_requested_sources",
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
            "backend.application.workbench.resolve_requested_sources",
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
        repository.task = WorkbenchTaskRecord(
            id="wb-1",
            task_kind="plan",
            status="queued",
            prompt="Plan",
            session_id=None,
            project_id=None,
            knowledge_document_ids=[],
            connector_ids=[],
            source_ids=[],
            created_at="2026-04-11T00:00:00+00:00",
            updated_at="2026-04-11T00:00:00+00:00",
            auth_scopes=["knowledge:read"],
            credential_id="cred-1",
            auth_mode="api_key",
            owner_id="owner-1",
            tenant_id="tenant-1",
            principal_id="principal-1",
        )

        from unittest.mock import patch

        with patch(
            "backend.application.workbench.authorize_workbench_task_read",
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
        repository.task = WorkbenchTaskRecord(
            id="wb-2",
            task_kind="canvas",
            status="completed",
            prompt="Draft",
            session_id="session-1",
            project_id=None,
            knowledge_document_ids=[],
            connector_ids=[],
            source_ids=[],
            created_at="2026-04-11T00:00:00+00:00",
            updated_at="2026-04-11T00:00:02+00:00",
            result_text="# Draft\n\nBody",
            auth_scopes=["knowledge:read"],
            credential_id="cred-1",
            auth_mode="api_key",
            owner_id="owner-1",
            tenant_id="tenant-1",
            principal_id="principal-1",
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
            )
        ]

        from unittest.mock import patch

        with patch(
            "backend.application.workbench.authorize_workbench_task_read",
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
