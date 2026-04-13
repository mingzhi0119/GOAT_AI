"""Declarative retrieval-source registry for workbench browse/research tasks."""

from __future__ import annotations

from backend.domain.authz_types import AuthorizationContext
from backend.domain.authorization import ResourceRef
from backend.services.authz_audit import emit_authorization_audit
from backend.services.authorizer import authorize_workbench_source_read
from backend.services.workbench_source_catalog import (
    WorkbenchSourceDescriptor,
    build_workbench_source_catalog,
    build_workbench_source_catalog_by_id,
)
from backend.types import Settings


def list_workbench_sources(
    *,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str = "",
) -> list[WorkbenchSourceDescriptor]:
    """Return the visible workbench retrieval sources for the current caller."""
    visible: list[WorkbenchSourceDescriptor] = []
    for descriptor in build_workbench_source_catalog(settings):
        decision = authorize_workbench_source_read(
            ctx=auth_context,
            required_scope=descriptor.required_scope,
            allowed_tenant_ids=descriptor.allowed_tenant_ids,
            allowed_principal_ids=descriptor.allowed_principal_ids,
            allowed_owner_ids=descriptor.allowed_owner_ids,
            require_owner_header=settings.require_session_owner,
        )
        emit_authorization_audit(
            ctx=auth_context,
            action="workbench.source.read",
            resource=ResourceRef(
                resource_type="workbench_source", resource_id=descriptor.source_id
            ),
            decision=decision,
            request_id=request_id,
        )
        if decision.allowed:
            visible.append(descriptor)
    return visible


def normalize_requested_source_ids(
    *,
    source_ids: list[str],
    connector_ids: list[str],
    knowledge_document_ids: list[str],
) -> list[str]:
    """Deduplicate user-requested source ids and infer knowledge when docs are attached."""
    normalized: list[str] = []
    for raw in [*source_ids, *connector_ids]:
        source_id = raw.strip()
        if source_id and source_id not in normalized:
            normalized.append(source_id)
    if knowledge_document_ids and "knowledge" not in normalized:
        normalized.append("knowledge")
    return normalized


def resolve_requested_sources(
    *,
    source_ids: list[str],
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str = "",
) -> list[WorkbenchSourceDescriptor]:
    """Resolve requested source ids and preserve auth-vs-unknown distinctions."""
    descriptors = build_workbench_source_catalog_by_id(settings)
    resolved: list[WorkbenchSourceDescriptor] = []
    missing: list[str] = []
    denied: list[str] = []
    for source_id in source_ids:
        descriptor = descriptors.get(source_id)
        if descriptor is None:
            missing.append(source_id)
            continue
        decision = authorize_workbench_source_read(
            ctx=auth_context,
            required_scope=descriptor.required_scope,
            allowed_tenant_ids=descriptor.allowed_tenant_ids,
            allowed_principal_ids=descriptor.allowed_principal_ids,
            allowed_owner_ids=descriptor.allowed_owner_ids,
            require_owner_header=settings.require_session_owner,
        )
        emit_authorization_audit(
            ctx=auth_context,
            action="workbench.source.read",
            resource=ResourceRef(
                resource_type="workbench_source", resource_id=descriptor.source_id
            ),
            decision=decision,
            request_id=request_id,
        )
        if not decision.allowed:
            if decision.conceal_existence:
                missing.append(source_id)
            else:
                denied.append(source_id)
            continue
        resolved.append(descriptor)
    if denied:
        joined = ", ".join(sorted(dict.fromkeys(denied)))
        raise PermissionError(
            f"Caller lacks permission to use the requested workbench sources: {joined}"
        )
    if missing:
        joined = ", ".join(sorted(dict.fromkeys(missing)))
        raise ValueError(f"Unknown or unavailable workbench sources: {joined}")
    return resolved
