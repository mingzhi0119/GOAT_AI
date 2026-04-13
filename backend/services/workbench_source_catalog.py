"""Shared workbench source-catalog and caller-visible source facts."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from backend.domain.authorization import Scope
from backend.services.workbench_web_search import (
    build_workbench_web_description,
    get_workbench_web_runtime_status,
)
from backend.types import Settings
from goat_ai.config.feature_gate_reasons import (
    RUNTIME_DISABLED_BY_OPERATOR,
    RUNTIME_NOT_IMPLEMENTED,
)
from goat_ai.shared.workbench_connector_bindings import (
    WorkbenchConnectorBinding,
    parse_workbench_connector_bindings_json,
)


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


@dataclass(frozen=True)
class WorkbenchVisibleSourceFacts:
    """Caller-visible source facts shared by capability and runtime assembly."""

    sources: tuple[WorkbenchSourceDescriptor, ...]

    def has_runnable_task_kind(self, task_kind: str) -> bool:
        return any(
            source.runtime_ready and task_kind in source.task_kinds
            for source in self.sources
        )

    def has_runnable_source_id(self, source_id: str) -> bool:
        return any(
            source.runtime_ready and source.source_id == source_id
            for source in self.sources
        )

    def has_runnable_source_kind(self, kind: str) -> bool:
        return any(
            source.runtime_ready and source.kind == kind for source in self.sources
        )


def build_visible_source_facts(
    sources: Iterable[WorkbenchSourceDescriptor],
) -> WorkbenchVisibleSourceFacts:
    """Normalize caller-visible sources into reusable capability predicates."""
    return WorkbenchVisibleSourceFacts(tuple(sources))


def build_workbench_source_catalog(
    settings: Settings,
) -> tuple[WorkbenchSourceDescriptor, ...]:
    """Build the full operator-configured source catalog before caller filtering."""
    web_runtime_ready, web_deny_reason = get_workbench_web_runtime_status(settings)
    readonly_runtime_ready, readonly_runtime_deny_reason = (
        _readonly_source_runtime_status(settings)
    )
    connector_descriptors = tuple(
        _connector_descriptor(
            binding=binding,
            runtime_ready=readonly_runtime_ready,
            deny_reason=readonly_runtime_deny_reason,
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
            runtime_ready=readonly_runtime_ready,
            deny_reason=readonly_runtime_deny_reason,
            description=(
                "Read-only retrieval over caller-visible durable workspace outputs "
                "for the requested project scope."
            ),
            requires_project_id=True,
        ),
        *connector_descriptors,
    )


def build_workbench_source_catalog_by_id(
    settings: Settings,
) -> dict[str, WorkbenchSourceDescriptor]:
    """Return the source catalog indexed by stable source id."""
    return {
        descriptor.source_id: descriptor
        for descriptor in build_workbench_source_catalog(settings)
    }


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
