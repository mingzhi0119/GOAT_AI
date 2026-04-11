from __future__ import annotations

import unittest

from backend.domain.authz_types import AuthorizationContext
from backend.domain.authorization import PrincipalId, TenantId
from backend.domain.resource_ownership import (
    DEFAULT_TENANT_ID,
    PersistedResourceOwnership,
    ownership_from_fields,
    ownership_from_resource,
)
from backend.services.artifact_service import PersistedArtifactRecord
from backend.services.chat_runtime import SessionSummaryRecord
from backend.services.code_sandbox_runtime import CodeSandboxExecutionRecord
from backend.services.knowledge_repository import KnowledgeDocumentRecord
from backend.services.media_service import MediaUploadRecord
from backend.services.workbench_runtime import WorkbenchTaskRecord


def _ctx() -> AuthorizationContext:
    return AuthorizationContext(
        principal_id=PrincipalId("principal:test"),
        tenant_id=TenantId("tenant:test"),
        scopes=frozenset(),  # type: ignore[arg-type]
        credential_id="cred:test",
        legacy_owner_id="owner:test",
        auth_mode="test",
    )


class PersistedResourceOwnershipTests(unittest.TestCase):
    def test_from_auth_context_captures_request_scoped_identity(self) -> None:
        ownership = PersistedResourceOwnership.from_auth_context(_ctx())
        self.assertEqual("owner:test", ownership.owner_id)
        self.assertEqual("tenant:test", ownership.tenant_id)
        self.assertEqual("principal:test", ownership.principal_id)

    def test_from_fields_applies_default_tenant(self) -> None:
        ownership = ownership_from_fields(owner_id="owner:test", tenant_id="")
        self.assertEqual("owner:test", ownership.owner_id)
        self.assertEqual(DEFAULT_TENANT_ID, ownership.tenant_id)
        self.assertEqual("", ownership.principal_id)

    def test_artifact_record_exposes_explicit_ownership(self) -> None:
        record = PersistedArtifactRecord(
            id="art-1",
            session_id="sess-1",
            owner_id="owner:test",
            tenant_id="tenant:test",
            principal_id="principal:test",
            filename="a.txt",
            mime_type="text/plain",
            byte_size=1,
            storage_path="a.txt",
            source_message_index=0,
            created_at="now",
        )
        self.assertEqual(
            PersistedResourceOwnership(
                owner_id="owner:test",
                tenant_id="tenant:test",
                principal_id="principal:test",
            ),
            record.ownership,
        )

    def test_session_record_exposes_explicit_ownership(self) -> None:
        record = SessionSummaryRecord(
            id="sess-1",
            title="title",
            model="m",
            schema_version=1,
            created_at="a",
            updated_at="b",
            owner_id="owner:test",
            tenant_id="tenant:test",
            principal_id="principal:test",
        )
        self.assertEqual("tenant:test", record.ownership.tenant_id)

    def test_knowledge_media_workbench_and_execution_records_expose_ownership(
        self,
    ) -> None:
        document = KnowledgeDocumentRecord(
            id="doc-1",
            source_type="upload",
            original_filename="f.txt",
            mime_type="text/plain",
            sha256="abc",
            storage_path="/tmp/f.txt",
            byte_size=1,
            status="ready",
            created_at="a",
            updated_at="b",
            deleted_at=None,
            owner_id="owner:test",
            tenant_id="tenant:test",
            principal_id="principal:test",
        )
        media = MediaUploadRecord(
            id="att-1",
            owner_id="owner:test",
            tenant_id="tenant:test",
            principal_id="principal:test",
            filename="a.png",
            mime_type="image/png",
            byte_size=1,
            storage_path="/tmp/a.png",
            width_px=1,
            height_px=1,
            created_at="now",
        )
        task = WorkbenchTaskRecord(
            id="task-1",
            task_kind="plan",
            status="queued",
            prompt="hello",
            session_id=None,
            project_id=None,
            knowledge_document_ids=[],
            connector_ids=[],
            source_ids=[],
            created_at="a",
            updated_at="b",
            owner_id="owner:test",
            tenant_id="tenant:test",
            principal_id="principal:test",
        )
        execution = CodeSandboxExecutionRecord(
            id="exec-1",
            status="queued",
            execution_mode="sync",
            runtime_preset="shell",
            network_policy="disabled",
            timeout_sec=5,
            code=None,
            command="echo hi",
            stdin=None,
            inline_files=[],
            created_at="a",
            queued_at="a",
            updated_at="a",
            owner_id="owner:test",
            tenant_id="tenant:test",
            principal_id="principal:test",
        )

        for resource in (document, media, task, execution):
            self.assertEqual("owner:test", resource.ownership.owner_id)
            self.assertEqual("tenant:test", resource.ownership.tenant_id)
            self.assertEqual("principal:test", resource.ownership.principal_id)

    def test_ownership_from_resource_falls_back_to_field_lookup(self) -> None:
        class LegacyResource:
            owner_id = "owner:test"
            tenant_id = "tenant:test"
            principal_id = "principal:test"

        ownership = ownership_from_resource(LegacyResource())
        self.assertEqual("owner:test", ownership.owner_id)
        self.assertEqual("tenant:test", ownership.tenant_id)
        self.assertEqual("principal:test", ownership.principal_id)
