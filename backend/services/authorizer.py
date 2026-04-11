from __future__ import annotations

from backend.domain.authz_types import AuthorizationContext
from backend.domain.authorization import AuthorizationDecision, Scope
from backend.services.artifact_service import PersistedArtifactRecord
from backend.services.chat_runtime import SessionDetailRecord, SessionSummaryRecord
from backend.services.knowledge_repository import KnowledgeDocumentRecord
from backend.services.workbench_runtime import WorkbenchTaskRecord


def _has_scope(ctx: AuthorizationContext, required_scope: str) -> bool:
    return required_scope in ctx.scopes


def _owner_visible(
    *,
    resource_owner_id: str,
    legacy_owner_id: str,
    require_owner_header: bool,
) -> bool:
    if require_owner_header and not legacy_owner_id:
        return False
    if not require_owner_header and not legacy_owner_id:
        return True
    if not resource_owner_id:
        return legacy_owner_id == ""
    return resource_owner_id == legacy_owner_id


def authorize_session_read(
    *,
    ctx: AuthorizationContext,
    session: SessionDetailRecord | SessionSummaryRecord,
    require_owner_header: bool,
) -> AuthorizationDecision:
    if not _has_scope(ctx, "history:read"):
        return AuthorizationDecision(False, "scope_missing")
    if session.tenant_id and session.tenant_id != ctx.tenant_id.value:
        return AuthorizationDecision(False, "tenant_mismatch", conceal_existence=True)
    if session.principal_id and session.principal_id != ctx.principal_id.value:
        return AuthorizationDecision(
            False, "principal_mismatch", conceal_existence=True
        )
    if not _owner_visible(
        resource_owner_id=session.owner_id,
        legacy_owner_id=ctx.legacy_owner_id,
        require_owner_header=require_owner_header,
    ):
        return AuthorizationDecision(False, "owner_mismatch", conceal_existence=True)
    return AuthorizationDecision(True, "ok")


def authorize_session_write(
    *,
    ctx: AuthorizationContext,
    session: SessionDetailRecord | SessionSummaryRecord,
    require_owner_header: bool,
) -> AuthorizationDecision:
    if not _has_scope(ctx, "history:write"):
        return AuthorizationDecision(False, "scope_missing")
    return authorize_session_read(
        ctx=ctx,
        session=session,
        require_owner_header=require_owner_header,
    )


def authorize_artifact_read(
    *,
    ctx: AuthorizationContext,
    artifact: PersistedArtifactRecord,
    require_owner_header: bool,
) -> AuthorizationDecision:
    if not _has_scope(ctx, "artifact:read"):
        return AuthorizationDecision(False, "scope_missing")
    if artifact.tenant_id and artifact.tenant_id != ctx.tenant_id.value:
        return AuthorizationDecision(False, "tenant_mismatch", conceal_existence=True)
    if artifact.principal_id and artifact.principal_id != ctx.principal_id.value:
        return AuthorizationDecision(
            False, "principal_mismatch", conceal_existence=True
        )
    if not _owner_visible(
        resource_owner_id=artifact.owner_id,
        legacy_owner_id=ctx.legacy_owner_id,
        require_owner_header=require_owner_header,
    ):
        return AuthorizationDecision(False, "owner_mismatch", conceal_existence=True)
    return AuthorizationDecision(True, "ok")


def authorize_knowledge_document_read(
    *,
    ctx: AuthorizationContext,
    document: KnowledgeDocumentRecord,
    require_owner_header: bool,
) -> AuthorizationDecision:
    if not _has_scope(ctx, "knowledge:read"):
        return AuthorizationDecision(False, "scope_missing")
    if document.tenant_id and document.tenant_id != ctx.tenant_id.value:
        return AuthorizationDecision(False, "tenant_mismatch", conceal_existence=True)
    if document.principal_id and document.principal_id != ctx.principal_id.value:
        return AuthorizationDecision(
            False, "principal_mismatch", conceal_existence=True
        )
    if not _owner_visible(
        resource_owner_id=document.owner_id,
        legacy_owner_id=ctx.legacy_owner_id,
        require_owner_header=require_owner_header,
    ):
        return AuthorizationDecision(False, "owner_mismatch", conceal_existence=True)
    return AuthorizationDecision(True, "ok")


def authorize_knowledge_document_write(
    *,
    ctx: AuthorizationContext,
    document: KnowledgeDocumentRecord,
    require_owner_header: bool,
) -> AuthorizationDecision:
    if not _has_scope(ctx, "knowledge:write"):
        return AuthorizationDecision(False, "scope_missing")
    return authorize_knowledge_document_read(
        ctx=ctx,
        document=document,
        require_owner_header=require_owner_header,
    )


def authorize_media_read(
    *,
    ctx: AuthorizationContext,
    media: object,
    require_owner_header: bool,
) -> AuthorizationDecision:
    if not _has_scope(ctx, "media:read"):
        return AuthorizationDecision(False, "scope_missing")
    tenant_id = str(getattr(media, "tenant_id", ""))
    principal_id = str(getattr(media, "principal_id", ""))
    owner_id = str(getattr(media, "owner_id", ""))
    if tenant_id and tenant_id != ctx.tenant_id.value:
        return AuthorizationDecision(False, "tenant_mismatch", conceal_existence=True)
    if principal_id and principal_id != ctx.principal_id.value:
        return AuthorizationDecision(
            False, "principal_mismatch", conceal_existence=True
        )
    if not _owner_visible(
        resource_owner_id=owner_id,
        legacy_owner_id=ctx.legacy_owner_id,
        require_owner_header=require_owner_header,
    ):
        return AuthorizationDecision(False, "owner_mismatch", conceal_existence=True)
    return AuthorizationDecision(True, "ok")


def authorize_workbench_task_read(
    *,
    ctx: AuthorizationContext,
    task: WorkbenchTaskRecord,
    require_owner_header: bool,
) -> AuthorizationDecision:
    """Authorize visibility for a persisted workbench task.

    Workbench MVP routes do not define a dedicated scope family yet, so the
    initial status-polling contract enforces tenant/principal/legacy-owner
    boundaries without introducing new credential scope strings.
    """
    if task.tenant_id and task.tenant_id != ctx.tenant_id.value:
        return AuthorizationDecision(False, "tenant_mismatch", conceal_existence=True)
    if task.principal_id and task.principal_id != ctx.principal_id.value:
        return AuthorizationDecision(
            False, "principal_mismatch", conceal_existence=True
        )
    if not _owner_visible(
        resource_owner_id=task.owner_id,
        legacy_owner_id=ctx.legacy_owner_id,
        require_owner_header=require_owner_header,
    ):
        return AuthorizationDecision(False, "owner_mismatch", conceal_existence=True)
    return AuthorizationDecision(True, "ok")


def authorize_workbench_source_read(
    *,
    ctx: AuthorizationContext,
    required_scope: Scope | None,
) -> AuthorizationDecision:
    """Authorize visibility for a declarative workbench retrieval source."""
    if required_scope is not None and not _has_scope(ctx, required_scope):
        return AuthorizationDecision(False, "scope_missing")
    return AuthorizationDecision(True, "ok")
