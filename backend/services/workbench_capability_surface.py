"""Shared workbench capability assembly for caller-scoped feature discovery."""

from __future__ import annotations

from collections.abc import Iterable

from backend.models.system import RuntimeFeaturePayload, WorkbenchFeaturePayload
from backend.services.workbench_source_catalog import (
    WorkbenchSourceDescriptor,
    build_visible_source_facts,
)
from goat_ai.config.feature_gate_reasons import RUNTIME_NOT_IMPLEMENTED
from goat_ai.config.feature_gates import RuntimeFeatureSnapshot


def build_workbench_feature_payload(
    *,
    snapshot: RuntimeFeatureSnapshot,
    workbench_read_allowed: bool,
    workbench_write_allowed: bool,
    artifact_export_allowed: bool,
    visible_sources: Iterable[WorkbenchSourceDescriptor],
) -> WorkbenchFeaturePayload:
    """Assemble caller-scoped workbench capability truth from shared source facts."""
    visible_source_facts = build_visible_source_facts(visible_sources)
    return WorkbenchFeaturePayload(
        agent_tasks=_runtime_payload(
            snapshot=snapshot,
            policy_allowed=workbench_write_allowed,
        ),
        plan_mode=_runtime_payload(
            snapshot=snapshot,
            policy_allowed=workbench_write_allowed,
        ),
        browse=_workbench_capability(
            snapshot=snapshot,
            policy_allowed=workbench_write_allowed,
            runtime_ready=visible_source_facts.has_runnable_task_kind("browse"),
        ),
        deep_research=_workbench_capability(
            snapshot=snapshot,
            policy_allowed=workbench_write_allowed,
            runtime_ready=visible_source_facts.has_runnable_task_kind("deep_research"),
        ),
        artifact_workspace=_workbench_capability(
            snapshot=snapshot,
            policy_allowed=workbench_read_allowed,
            runtime_ready=True,
        ),
        artifact_exports=_workbench_capability(
            snapshot=snapshot,
            policy_allowed=artifact_export_allowed,
            runtime_ready=True,
        ),
        project_memory=_workbench_capability(
            snapshot=snapshot,
            policy_allowed=workbench_read_allowed,
            runtime_ready=visible_source_facts.has_runnable_source_id("project_memory"),
        ),
        connectors=_workbench_capability(
            snapshot=snapshot,
            policy_allowed=workbench_write_allowed,
            runtime_ready=visible_source_facts.has_runnable_source_kind("connector"),
        ),
    )


def _runtime_payload(
    *,
    snapshot: RuntimeFeatureSnapshot,
    policy_allowed: bool,
) -> RuntimeFeaturePayload:
    return RuntimeFeaturePayload(
        allowed_by_config=snapshot.allowed_by_config and policy_allowed,
        available_on_host=snapshot.available_on_host,
        effective_enabled=snapshot.effective_enabled and policy_allowed,
        deny_reason=(
            snapshot.deny_reason
            if not snapshot.effective_enabled
            else (None if policy_allowed else "permission_denied")
        ),
    )


def _workbench_capability(
    *,
    snapshot: RuntimeFeatureSnapshot,
    policy_allowed: bool,
    runtime_ready: bool,
    deny_reason: str | None = None,
) -> RuntimeFeaturePayload:
    if not snapshot.allowed_by_config:
        return _runtime_payload(snapshot=snapshot, policy_allowed=policy_allowed)
    return RuntimeFeaturePayload(
        allowed_by_config=policy_allowed,
        available_on_host=runtime_ready,
        effective_enabled=snapshot.effective_enabled
        and policy_allowed
        and runtime_ready,
        deny_reason=(
            "permission_denied"
            if not policy_allowed
            else (None if runtime_ready else (deny_reason or RUNTIME_NOT_IMPLEMENTED))
        ),
    )
