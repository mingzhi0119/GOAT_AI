from __future__ import annotations

import logging

from backend.domain.authz_types import AuthorizationContext
from backend.domain.authorization import AuthorizationDecision, ResourceRef

logger = logging.getLogger("goat_ai.authz")


def emit_authorization_audit(
    *,
    ctx: AuthorizationContext,
    action: str,
    resource: ResourceRef,
    decision: AuthorizationDecision,
    request_id: str,
) -> None:
    logger.info(
        "authorization_decision",
        extra={
            "event": "authorization_decision",
            "principal_id": ctx.principal_id.value,
            "tenant_id": ctx.tenant_id.value,
            "credential_id": ctx.credential_id,
            "action": action,
            "resource_type": resource.resource_type,
            "resource_id": resource.resource_id,
            "result": "allow" if decision.allowed else "deny",
            "reason_code": decision.reason_code,
            "request_id": request_id,
        },
    )
