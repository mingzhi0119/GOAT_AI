"""Declarative retrieval-source registry for workbench browse/research tasks."""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.authz_types import AuthorizationContext
from backend.domain.authorization import ResourceRef, Scope
from backend.services.authz_audit import emit_authorization_audit
from backend.services.authorizer import authorize_workbench_source_read
from backend.types import Settings


@dataclass(frozen=True, kw_only=True)
class WorkbenchSourceDescriptor:
    """One declarative retrieval source exposed to workbench tasks."""

    source_id: str
    display_name: str
    kind: str
    scope_kind: str
    capabilities: tuple[str, ...]
    task_kinds: tuple[str, ...]
    read_only: bool
    runtime_ready: bool
    deny_reason: str | None
    description: str
    required_scope: Scope | None = None


def list_workbench_sources(
    *,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str = "",
) -> list[WorkbenchSourceDescriptor]:
    """Return the visible workbench retrieval sources for the current caller."""
    visible: list[WorkbenchSourceDescriptor] = []
    for descriptor in _all_source_descriptors(settings):
        decision = authorize_workbench_source_read(
            ctx=auth_context,
            required_scope=descriptor.required_scope,
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
    """Resolve requested source ids against the visible registry entries."""
    visible = {
        descriptor.source_id: descriptor
        for descriptor in list_workbench_sources(
            settings=settings,
            auth_context=auth_context,
            request_id=request_id,
        )
    }
    resolved: list[WorkbenchSourceDescriptor] = []
    missing: list[str] = []
    for source_id in source_ids:
        descriptor = visible.get(source_id)
        if descriptor is None:
            missing.append(source_id)
            continue
        resolved.append(descriptor)
    if missing:
        joined = ", ".join(sorted(dict.fromkeys(missing)))
        raise ValueError(f"Unknown or unavailable workbench sources: {joined}")
    return resolved


def _all_source_descriptors(
    settings: Settings,
) -> tuple[WorkbenchSourceDescriptor, ...]:
    _ = settings
    return (
        WorkbenchSourceDescriptor(
            source_id="web",
            display_name="Public Web",
            kind="builtin",
            scope_kind="global",
            capabilities=("search", "fetch", "citations"),
            task_kinds=("browse", "deep_research"),
            read_only=True,
            runtime_ready=False,
            deny_reason="not_implemented",
            description=(
                "Future public-web retrieval source for browse and deep research tasks."
            ),
            required_scope=None,
        ),
        WorkbenchSourceDescriptor(
            source_id="knowledge",
            display_name="Knowledge Base",
            kind="knowledge",
            scope_kind="knowledge_documents",
            capabilities=("search", "fetch", "citations"),
            task_kinds=("plan", "browse", "deep_research"),
            read_only=True,
            runtime_ready=True,
            deny_reason=None,
            description=(
                "Indexed GOAT AI knowledge documents scoped by tenant, principal, and owner visibility."
            ),
            required_scope="knowledge:read",
        ),
    )
