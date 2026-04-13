"""Shared helpers for workbench application modules."""

from __future__ import annotations

from datetime import datetime, timezone

from backend.application.exceptions import (
    WorkbenchPermissionDeniedError,
    WorkbenchSourceValidationError,
    WorkbenchTaskNotFoundError,
    WorkbenchWorkspaceOutputNotFoundError,
)
from backend.application.ports import Settings, WorkbenchTaskRepository
from backend.domain.authz_types import AuthorizationContext
from backend.models.artifact import ChatArtifact
from backend.models.knowledge import KnowledgeCitation
from backend.models.workbench import (
    WorkbenchSourcePayload,
    WorkbenchTaskAcceptedResponse,
    WorkbenchTaskEventPayload,
    WorkbenchTaskResultPayload,
    WorkbenchTaskStatusResponse,
    WorkbenchWorkspaceOutputPayload,
)
from backend.services.authorizer import (
    authorize_workbench_output_read,
    authorize_workbench_task_read,
    authorize_workbench_task_write,
)
from backend.services.feature_gate_service import require_agent_workbench_enabled
from backend.services.workbench_source_catalog import WorkbenchSourceDescriptor
from backend.services.workbench_runtime import (
    WorkbenchTaskCreatePayload,
    WorkbenchTaskEventRecord,
    WorkbenchTaskRecord,
    WorkbenchWorkspaceOutputRecord,
)


def ensure_agent_workbench_enabled(settings: Settings) -> None:
    """Enforce the shared runtime gate for future agent/workbench tasks."""
    require_agent_workbench_enabled(settings)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_accepted_response(task: WorkbenchTaskRecord) -> WorkbenchTaskAcceptedResponse:
    return WorkbenchTaskAcceptedResponse(
        task_id=task.id,
        task_kind=task.task_kind,
        status=task.status,
        created_at=task.created_at,
    )


def to_status_response(task: WorkbenchTaskRecord) -> WorkbenchTaskStatusResponse:
    return WorkbenchTaskStatusResponse(
        task_id=task.id,
        task_kind=task.task_kind,
        status=task.status,
        created_at=task.created_at,
        updated_at=task.updated_at,
        error_detail=task.error_detail,
        result=(
            WorkbenchTaskResultPayload(
                content=task.result_text,
                citations=[
                    KnowledgeCitation.model_validate(item)
                    for item in (task.result_citations or [])
                ],
            )
            if task.result_text is not None
            else None
        ),
        workspace_outputs=[],
    )


def to_workspace_output_payload(
    output: WorkbenchWorkspaceOutputRecord,
) -> WorkbenchWorkspaceOutputPayload:
    metadata = dict(output.metadata or {})
    artifact_items = metadata.pop("artifacts", [])
    return WorkbenchWorkspaceOutputPayload(
        output_id=output.id,
        output_kind=output.output_kind,
        title=output.title,
        content_format=output.content_format,
        content=output.content_text,
        created_at=output.created_at,
        updated_at=output.updated_at,
        metadata=metadata,
        artifacts=[
            ChatArtifact.model_validate(item)
            for item in artifact_items
            if isinstance(item, dict)
        ],
    )


def filter_visible_workspace_outputs(
    *,
    outputs: list[WorkbenchWorkspaceOutputRecord],
    settings: Settings,
    auth_context: AuthorizationContext,
) -> list[WorkbenchWorkspaceOutputPayload]:
    visible: list[WorkbenchWorkspaceOutputPayload] = []
    for output in outputs:
        decision = authorize_workbench_output_read(
            ctx=auth_context,
            output=output,
            require_owner_header=settings.require_session_owner,
        )
        if decision.allowed:
            visible.append(to_workspace_output_payload(output))
    return visible


def to_event_payload(event: WorkbenchTaskEventRecord) -> WorkbenchTaskEventPayload:
    return WorkbenchTaskEventPayload(
        sequence=event.sequence,
        event_type=event.event_type,
        created_at=event.created_at,
        status=event.status,
        message=event.message,
        metadata=dict(event.metadata or {}),
    )


def to_source_payload(source: WorkbenchSourceDescriptor) -> WorkbenchSourcePayload:
    return WorkbenchSourcePayload(
        source_id=source.source_id,
        display_name=source.display_name,
        kind=source.kind,
        scope_kind=source.scope_kind,
        capabilities=list(source.capabilities),
        task_kinds=list(source.task_kinds),
        read_only=source.read_only,
        runtime_ready=source.runtime_ready,
        deny_reason=source.deny_reason,
        description=source.description,
    )


def ensure_sources_support_task_kind(
    *,
    task_kind: str,
    sources: list[WorkbenchSourceDescriptor],
) -> None:
    incompatible = sorted(
        source.source_id for source in sources if task_kind not in source.task_kinds
    )
    if incompatible:
        joined = ", ".join(incompatible)
        raise WorkbenchSourceValidationError(
            f"Requested workbench sources do not support task kind {task_kind!r}: {joined}."
        )


def ensure_source_requirements(
    *,
    project_id: str | None,
    sources: list[WorkbenchSourceDescriptor],
) -> None:
    if any(source.requires_project_id for source in sources) and not project_id:
        raise WorkbenchSourceValidationError(
            "Requested workbench sources require project_id: project_memory."
        )


def build_task_create_payload(
    *,
    task_id: str,
    task_kind: str,
    prompt: str,
    session_id: str | None,
    project_id: str | None,
    knowledge_document_ids: list[str],
    connector_ids: list[str],
    source_ids: list[str],
    created_at: str,
    owner_id: str,
    tenant_id: str,
    principal_id: str,
    auth_scopes: list[str] | None,
    credential_id: str,
    auth_mode: str,
) -> WorkbenchTaskCreatePayload:
    return WorkbenchTaskCreatePayload(
        task_id=task_id,
        task_kind=task_kind,
        prompt=prompt,
        session_id=session_id,
        project_id=project_id,
        knowledge_document_ids=list(knowledge_document_ids),
        connector_ids=list(connector_ids),
        source_ids=list(source_ids),
        created_at=created_at,
        updated_at=created_at,
        owner_id=owner_id,
        tenant_id=tenant_id,
        principal_id=principal_id,
        auth_scopes=list(auth_scopes or []),
        credential_id=credential_id,
        auth_mode=auth_mode,
    )


def load_visible_task(
    *,
    task_id: str,
    repository: WorkbenchTaskRepository,
    settings: Settings,
    auth_context: AuthorizationContext,
    access_mode: str = "read",
) -> WorkbenchTaskRecord:
    ensure_agent_workbench_enabled(settings)
    task = repository.get_task(task_id)
    if task is None:
        raise WorkbenchTaskNotFoundError("Workbench task not found")
    if access_mode == "write":
        decision = authorize_workbench_task_write(
            ctx=auth_context,
            task=task,
            require_owner_header=settings.require_session_owner,
        )
    else:
        decision = authorize_workbench_task_read(
            ctx=auth_context,
            task=task,
            require_owner_header=settings.require_session_owner,
        )
    if not decision.allowed:
        if decision.reason_code == "scope_missing":
            raise WorkbenchPermissionDeniedError(
                "Caller lacks the scopes required for this workbench task."
            )
        raise WorkbenchTaskNotFoundError("Workbench task not found")
    return task


def load_visible_workspace_output(
    *,
    output_id: str,
    repository: WorkbenchTaskRepository,
    settings: Settings,
    auth_context: AuthorizationContext,
) -> WorkbenchWorkspaceOutputRecord:
    ensure_agent_workbench_enabled(settings)
    output = repository.get_workspace_output(output_id)
    if output is None:
        raise WorkbenchWorkspaceOutputNotFoundError(
            "Workbench workspace output not found"
        )
    decision = authorize_workbench_output_read(
        ctx=auth_context,
        output=output,
        require_owner_header=settings.require_session_owner,
    )
    if not decision.allowed:
        if decision.reason_code == "scope_missing":
            raise WorkbenchPermissionDeniedError(
                "Caller lacks the scopes required for this workbench output."
            )
        raise WorkbenchWorkspaceOutputNotFoundError(
            "Workbench workspace output not found"
        )
    return output
