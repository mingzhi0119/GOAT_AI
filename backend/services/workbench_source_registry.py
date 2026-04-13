"""Declarative retrieval-source registry for workbench browse/research tasks."""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.authz_types import AuthorizationContext
from backend.domain.authorization import ResourceRef, Scope
from backend.services.authz_audit import emit_authorization_audit
from backend.services.authorizer import authorize_workbench_source_read
from goat_ai.config.feature_gate_reasons import (
    RUNTIME_DISABLED_BY_OPERATOR,
    RUNTIME_NOT_IMPLEMENTED,
)
from goat_ai.shared.workbench_connector_bindings import (
    WorkbenchConnectorBinding,
    parse_workbench_connector_bindings_json,
)
from backend.services.workbench_web_search import (
    build_workbench_web_description,
    get_workbench_web_runtime_status,
)
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
    allowed_tenant_ids: tuple[str, ...] = ()
    allowed_principal_ids: tuple[str, ...] = ()
    allowed_owner_ids: tuple[str, ...] = ()
    requires_project_id: bool = False


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
    descriptors = {
        descriptor.source_id: descriptor
        for descriptor in _all_source_descriptors(settings)
    }
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


def _all_source_descriptors(
    settings: Settings,
) -> tuple[WorkbenchSourceDescriptor, ...]:
    web_runtime_ready, web_deny_reason = get_workbench_web_runtime_status(settings)
    runtime_ready, runtime_deny_reason = _readonly_source_runtime_status(settings)
    connector_descriptors = tuple(
        _connector_descriptor(
            binding=binding,
            runtime_ready=runtime_ready,
            deny_reason=runtime_deny_reason,
        )
        for binding in parse_workbench_connector_bindings_json(
            settings.workbench_connector_bindings_json
        )
    )
    return (
        WorkbenchSourceDescriptor(
            source_id="web",
            display_name="Public Web",
            kind="builtin",
            scope_kind="global",
            capabilities=("search", "citations"),
            task_kinds=("browse", "deep_research"),
            read_only=True,
            runtime_ready=web_runtime_ready,
            deny_reason=web_deny_reason,
            description=build_workbench_web_description(settings),
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
        WorkbenchSourceDescriptor(
            source_id="project_memory",
            display_name="Project Memory",
            kind="project_memory",
            scope_kind="project_scope",
            capabilities=("search", "citations"),
            task_kinds=("browse", "deep_research"),
            read_only=True,
            runtime_ready=runtime_ready,
            deny_reason=runtime_deny_reason,
            description=(
                "Read-only retrieval over caller-visible durable workspace outputs "
                "for the requested project scope."
            ),
            requires_project_id=True,
        ),
        *connector_descriptors,
    )


def _readonly_source_runtime_status(settings: Settings) -> tuple[bool, str | None]:
    if not settings.workbench_langgraph_enabled:
        return False, RUNTIME_DISABLED_BY_OPERATOR
    try:
        from langgraph.graph import END, START, StateGraph  # noqa: F401
    except ImportError:
        return False, RUNTIME_NOT_IMPLEMENTED
    return True, None


def _connector_descriptor(
    *,
    binding: WorkbenchConnectorBinding,
    runtime_ready: bool,
    deny_reason: str | None,
) -> WorkbenchSourceDescriptor:
    return WorkbenchSourceDescriptor(
        source_id=binding.source_id,
        display_name=binding.display_name,
        kind="connector",
        scope_kind="connector_binding",
        capabilities=binding.capabilities,
        task_kinds=binding.task_kinds,
        read_only=True,
        runtime_ready=runtime_ready,
        deny_reason=deny_reason,
        description=binding.description,
        allowed_tenant_ids=binding.tenant_ids,
        allowed_principal_ids=binding.principal_ids,
        allowed_owner_ids=binding.owner_ids,
    )
