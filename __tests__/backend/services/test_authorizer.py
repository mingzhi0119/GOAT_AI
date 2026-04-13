from __future__ import annotations

import unittest

from backend.domain.authz_types import AuthorizationContext
from backend.services.authorizer import (
    authorize_artifact_read,
    authorize_session_read,
    authorize_workbench_output_export,
    authorize_workbench_task_read,
)
from backend.domain.authorization import PrincipalId, TenantId
from backend.services.artifact_service import PersistedArtifactRecord
from backend.services.chat_runtime import SessionDetailRecord
from backend.services.workbench_runtime import (
    WorkbenchTaskRecord,
    WorkbenchWorkspaceOutputRecord,
)


def _ctx(*, scopes: frozenset[str], owner: str = "alice") -> AuthorizationContext:
    return AuthorizationContext(
        principal_id=PrincipalId("principal:test"),
        tenant_id=TenantId("tenant:test"),
        scopes=scopes,  # type: ignore[arg-type]
        credential_id="cred:test",
        legacy_owner_id=owner,
        auth_mode="test",
    )


class AuthorizerTests(unittest.TestCase):
    def test_same_tenant_different_principal_still_allows_owned_artifact_read(
        self,
    ) -> None:
        decision = authorize_artifact_read(
            ctx=AuthorizationContext(
                principal_id=PrincipalId("principal:reader"),
                tenant_id=TenantId("tenant:test"),
                scopes=frozenset({"artifact:read"}),
                credential_id="cred:reader",
                legacy_owner_id="alice",
                auth_mode="test",
            ),
            artifact=PersistedArtifactRecord(
                id="art-1",
                session_id="sess-1",
                owner_id="alice",
                filename="a.txt",
                mime_type="text/plain",
                byte_size=1,
                storage_path="a.txt",
                source_message_index=0,
                created_at="now",
                tenant_id="tenant:test",
                principal_id="principal:writer",
            ),
            require_owner_header=False,
        )
        self.assertTrue(decision.allowed)
        self.assertEqual("ok", decision.reason_code)

    def test_scope_missing_denies_with_403_semantics(self) -> None:
        decision = authorize_session_read(
            ctx=_ctx(scopes=frozenset({"artifact:read"})),
            session=SessionDetailRecord(
                id="sess-1",
                title="t",
                model="m",
                schema_version=1,
                created_at="a",
                updated_at="b",
                owner_id="alice",
                tenant_id="tenant:test",
                principal_id="principal:test",
                messages=[],
            ),
            require_owner_header=False,
        )
        self.assertFalse(decision.allowed)
        self.assertEqual("scope_missing", decision.reason_code)
        self.assertFalse(decision.conceal_existence)

    def test_tenant_mismatch_conceals(self) -> None:
        decision = authorize_session_read(
            ctx=_ctx(scopes=frozenset({"history:read"})),
            session=SessionDetailRecord(
                id="sess-1",
                title="t",
                model="m",
                schema_version=1,
                created_at="a",
                updated_at="b",
                owner_id="alice",
                tenant_id="tenant:other",
                principal_id="principal:test",
                messages=[],
            ),
            require_owner_header=False,
        )
        self.assertFalse(decision.allowed)
        self.assertEqual("tenant_mismatch", decision.reason_code)
        self.assertTrue(decision.conceal_existence)

    def test_same_tenant_same_principal_allows(self) -> None:
        decision = authorize_artifact_read(
            ctx=_ctx(scopes=frozenset({"artifact:read"})),
            artifact=PersistedArtifactRecord(
                id="art-1",
                session_id="sess-1",
                owner_id="alice",
                filename="a.txt",
                mime_type="text/plain",
                byte_size=1,
                storage_path="a.txt",
                source_message_index=0,
                created_at="now",
                tenant_id="tenant:test",
                principal_id="principal:test",
            ),
            require_owner_header=False,
        )
        self.assertTrue(decision.allowed)
        self.assertEqual("ok", decision.reason_code)

    def test_owner_fallback_can_conceal(self) -> None:
        decision = authorize_artifact_read(
            ctx=_ctx(scopes=frozenset({"artifact:read"}), owner="bob"),
            artifact=PersistedArtifactRecord(
                id="art-1",
                session_id="sess-1",
                owner_id="alice",
                filename="a.txt",
                mime_type="text/plain",
                byte_size=1,
                storage_path="a.txt",
                source_message_index=0,
                created_at="now",
                tenant_id="tenant:test",
                principal_id="principal:test",
            ),
            require_owner_header=False,
        )
        self.assertFalse(decision.allowed)
        self.assertEqual("owner_mismatch", decision.reason_code)
        self.assertTrue(decision.conceal_existence)

    def test_workbench_scope_missing_denies_with_403_semantics(self) -> None:
        decision = authorize_workbench_task_read(
            ctx=_ctx(scopes=frozenset({"history:read"})),
            task=WorkbenchTaskRecord(
                id="wb-1",
                task_kind="plan",
                status="queued",
                prompt="Plan",
                session_id=None,
                project_id=None,
                knowledge_document_ids=[],
                connector_ids=[],
                source_ids=[],
                created_at="a",
                updated_at="b",
                owner_id="alice",
                tenant_id="tenant:test",
                principal_id="principal:test",
            ),
            require_owner_header=False,
        )
        self.assertFalse(decision.allowed)
        self.assertEqual("scope_missing", decision.reason_code)
        self.assertFalse(decision.conceal_existence)

    def test_workbench_export_owner_mismatch_stays_concealed(self) -> None:
        decision = authorize_workbench_output_export(
            ctx=_ctx(
                scopes=frozenset(
                    {"workbench:read", "workbench:export", "artifact:write"}
                ),
                owner="bob",
            ),
            output=WorkbenchWorkspaceOutputRecord(
                id="wbo-1",
                task_id="wb-1",
                output_kind="canvas_document",
                title="Draft",
                content_format="markdown",
                content_text="# Draft",
                created_at="a",
                updated_at="b",
                owner_id="alice",
                tenant_id="tenant:test",
                principal_id="principal:test",
            ),
            require_owner_header=False,
        )
        self.assertFalse(decision.allowed)
        self.assertEqual("owner_mismatch", decision.reason_code)
        self.assertTrue(decision.conceal_existence)
