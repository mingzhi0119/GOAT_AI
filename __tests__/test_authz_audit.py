from __future__ import annotations

import unittest
from unittest.mock import patch

from backend.application.authz_types import AuthorizationContext
from backend.domain.authorization import (
    AuthorizationDecision,
    PrincipalId,
    ResourceRef,
    TenantId,
)
from backend.services.authz_audit import emit_authorization_audit


class AuthzAuditTests(unittest.TestCase):
    def test_emit_contains_stable_identifiers_only(self) -> None:
        ctx = AuthorizationContext(
            principal_id=PrincipalId("principal:test"),
            tenant_id=TenantId("tenant:test"),
            scopes=frozenset({"history:read"}),  # type: ignore[arg-type]
            credential_id="cred:test",
            legacy_owner_id="alice",
            auth_mode="test",
        )
        decision = AuthorizationDecision(True, "ok")
        with patch("backend.services.authz_audit.logger.info") as info:
            emit_authorization_audit(
                ctx=ctx,
                action="history.session.read",
                resource=ResourceRef(resource_type="session", resource_id="sess-1"),
                decision=decision,
                request_id="req-1",
            )
        _, kwargs = info.call_args
        extra = kwargs["extra"]
        self.assertEqual("principal:test", extra["principal_id"])
        self.assertEqual("tenant:test", extra["tenant_id"])
        self.assertEqual("allow", extra["result"])
        self.assertNotIn("secret", extra)
        self.assertNotIn("api_key", extra)
