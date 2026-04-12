from __future__ import annotations

import unittest
from pathlib import Path

from backend.application.exceptions import (
    HistoryOwnerRequiredError,
    HistorySessionNotFoundError,
    HistoryValidationError,
)
from backend.application.history import (
    get_history_session_detail,
    rename_history_session,
    resolve_owner_filter,
)
from backend.domain.authz_types import AuthorizationContext
from backend.domain.authorization import PrincipalId, TenantId
from backend.models.chat import ChatMessage
from backend.services.chat_runtime import SessionUpsertPayload
from backend.services.session_message_codec import build_session_payload
from backend.services.workbench_runtime import WorkbenchWorkspaceOutputRecord
from goat_ai.config import Settings

from __tests__.test_fake_session_repository import InMemorySessionRepository


class _FakeWorkbenchRepository:
    def __init__(self) -> None:
        self.outputs: list[WorkbenchWorkspaceOutputRecord] = []

    def list_workspace_outputs_for_session(
        self, session_id: str
    ) -> list[WorkbenchWorkspaceOutputRecord]:
        return [output for output in self.outputs if output.session_id == session_id]


def _settings(*, require_owner: bool) -> Settings:
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
        require_session_owner=require_owner,
    )


def _auth_context(owner_id: str = "owner-1") -> AuthorizationContext:
    return AuthorizationContext(
        principal_id=PrincipalId("principal-1"),
        tenant_id=TenantId("tenant-1"),
        scopes=frozenset({"history:read", "history:write"}),
        credential_id="cred-1",
        legacy_owner_id=owner_id,
        auth_mode="api_key",
    )


class ApplicationHistoryTests(unittest.TestCase):
    def test_resolve_owner_filter_requires_owner_when_enabled(self) -> None:
        with self.assertRaises(HistoryOwnerRequiredError):
            resolve_owner_filter(
                settings=_settings(require_owner=True), request_owner=""
            )

    def test_rename_history_session_trims_title_before_persisting(self) -> None:
        repository = InMemorySessionRepository()
        payload = build_session_payload(
            messages=[ChatMessage(role="user", content="hello")],
            assistant_text="world",
            chart_spec=None,
            knowledge_documents=None,
            chart_data_source="none",
        )
        repository.upsert_session(
            SessionUpsertPayload(
                session_id="sess-1",
                title="Original",
                model="gemma4:26b",
                schema_version=2,
                payload=payload,
                created_at="2026-04-11T00:00:00+00:00",
                updated_at="2026-04-11T00:00:00+00:00",
                owner_id="owner-1",
                tenant_id="tenant-1",
                principal_id="principal-1",
            )
        )

        rename_history_session(
            repository=repository,
            session_id="sess-1",
            title="  Updated title  ",
            settings=_settings(require_owner=True),
            auth_context=_auth_context(),
            request_id="req-1",
        )

        detail = repository.get_session("sess-1")
        assert detail is not None
        self.assertEqual("Updated title", detail.title)

    def test_rename_history_session_rejects_empty_titles(self) -> None:
        with self.assertRaises(HistoryValidationError):
            rename_history_session(
                repository=InMemorySessionRepository(),
                session_id="missing",
                title="   ",
                settings=_settings(require_owner=False),
                auth_context=_auth_context(),
                request_id="req-1",
            )

    def test_get_history_session_detail_normalizes_optional_fields(self) -> None:
        repository = InMemorySessionRepository()
        payload = build_session_payload(
            messages=[ChatMessage(role="user", content="hello")],
            assistant_text="world",
            chart_spec=None,
            knowledge_documents=[
                {
                    "document_id": "doc-1",
                    "filename": "notes.md",
                    "mime_type": "text/markdown",
                }
            ],
            chart_data_source="none",
        )
        payload["file_context_prompt"] = "Attached context"
        repository.upsert_session(
            SessionUpsertPayload(
                session_id="sess-1",
                title="Original",
                model="gemma4:26b",
                schema_version=2,
                payload=payload,
                created_at="2026-04-11T00:00:00+00:00",
                updated_at="2026-04-11T00:00:00+00:00",
                owner_id="owner-1",
                tenant_id="tenant-1",
                principal_id="principal-1",
            )
        )

        detail = get_history_session_detail(
            repository=repository,
            workbench_repository=None,
            session_id="sess-1",
            settings=_settings(require_owner=True),
            auth_context=_auth_context(),
            request_id="req-1",
        )

        self.assertEqual("Attached context", detail.file_context.prompt)
        self.assertEqual("doc-1", detail.knowledge_documents[0].document_id)

    def test_get_history_session_detail_conceals_unauthorized_sessions(self) -> None:
        repository = InMemorySessionRepository()
        payload = build_session_payload(
            messages=[ChatMessage(role="user", content="hello")],
            assistant_text="world",
            chart_spec=None,
            knowledge_documents=None,
            chart_data_source="none",
        )
        repository.upsert_session(
            SessionUpsertPayload(
                session_id="sess-1",
                title="Original",
                model="gemma4:26b",
                schema_version=2,
                payload=payload,
                created_at="2026-04-11T00:00:00+00:00",
                updated_at="2026-04-11T00:00:00+00:00",
                owner_id="owner-1",
                tenant_id="tenant-1",
                principal_id="principal-1",
            )
        )

        with self.assertRaises(HistorySessionNotFoundError):
            get_history_session_detail(
                repository=repository,
                workbench_repository=None,
                session_id="sess-1",
                settings=_settings(require_owner=True),
                auth_context=_auth_context(owner_id="other-owner"),
                request_id="req-1",
            )

    def test_get_history_session_detail_includes_visible_workspace_outputs(
        self,
    ) -> None:
        repository = InMemorySessionRepository()
        workbench_repository = _FakeWorkbenchRepository()
        payload = build_session_payload(
            messages=[ChatMessage(role="user", content="hello")],
            assistant_text="world",
            chart_spec=None,
            knowledge_documents=None,
            chart_data_source="none",
        )
        repository.upsert_session(
            SessionUpsertPayload(
                session_id="sess-restore",
                title="Original",
                model="gemma4:26b",
                schema_version=2,
                payload=payload,
                created_at="2026-04-11T00:00:00+00:00",
                updated_at="2026-04-11T00:00:00+00:00",
                owner_id="owner-1",
                tenant_id="tenant-1",
                principal_id="principal-1",
            )
        )
        workbench_repository.outputs = [
            WorkbenchWorkspaceOutputRecord(
                id="wbo-1",
                task_id="wb-1",
                output_kind="canvas_document",
                title="Canvas",
                content_format="markdown",
                content_text="# Canvas",
                created_at="2026-04-11T00:00:01+00:00",
                updated_at="2026-04-11T00:00:02+00:00",
                session_id="sess-restore",
                metadata={"editable": True},
                owner_id="owner-1",
                tenant_id="tenant-1",
                principal_id="principal-1",
            )
        ]

        detail = get_history_session_detail(
            repository=repository,
            workbench_repository=workbench_repository,
            session_id="sess-restore",
            settings=_settings(require_owner=True),
            auth_context=_auth_context(),
            request_id="req-1",
        )

        self.assertEqual(1, len(detail.workspace_outputs))
        self.assertEqual("wbo-1", detail.workspace_outputs[0].output_id)
