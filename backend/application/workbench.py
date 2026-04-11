"""Workbench task entrypoints."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from backend.application.exceptions import (
    WorkbenchSourceValidationError,
    WorkbenchTaskNotFoundError,
)
from backend.application.ports import (
    Settings,
    WorkbenchTaskDispatcher,
    WorkbenchTaskRepository,
)
from backend.domain.authz_types import AuthorizationContext
from backend.models.workbench import (
    WorkbenchTaskAcceptedResponse,
    WorkbenchTaskEventPayload,
    WorkbenchTaskEventsResponse,
    WorkbenchTaskRequest,
    WorkbenchTaskResultPayload,
    WorkbenchWorkspaceOutputPayload,
    WorkbenchSourcePayload,
    WorkbenchSourcesResponse,
    WorkbenchTaskStatusResponse,
)
from backend.models.knowledge import KnowledgeCitation
from backend.services.authorizer import authorize_workbench_task_read
from backend.services.feature_gate_service import require_agent_workbench_enabled
from backend.services.workbench_runtime import (
    WorkbenchTaskCreatePayload,
    WorkbenchTaskEventRecord,
    WorkbenchTaskRecord,
    WorkbenchWorkspaceOutputRecord,
)
from backend.services.workbench_source_registry import (
    WorkbenchSourceDescriptor,
    list_workbench_sources,
    normalize_requested_source_ids,
    resolve_requested_sources,
)


def ensure_agent_workbench_enabled(settings: Settings) -> None:
    """Enforce the shared runtime gate for future agent/workbench tasks."""
    require_agent_workbench_enabled(settings)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_accepted_response(task: WorkbenchTaskRecord) -> WorkbenchTaskAcceptedResponse:
    return WorkbenchTaskAcceptedResponse(
        task_id=task.id,
        task_kind=task.task_kind,
        status=task.status,
        created_at=task.created_at,
    )


def _to_status_response(task: WorkbenchTaskRecord) -> WorkbenchTaskStatusResponse:
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


def _to_workspace_output_payload(
    output: WorkbenchWorkspaceOutputRecord,
) -> WorkbenchWorkspaceOutputPayload:
    return WorkbenchWorkspaceOutputPayload(
        output_id=output.id,
        output_kind=output.output_kind,
        title=output.title,
        content_format=output.content_format,
        content=output.content_text,
        created_at=output.created_at,
        updated_at=output.updated_at,
        metadata=dict(output.metadata or {}),
    )


def _to_event_payload(event: WorkbenchTaskEventRecord) -> WorkbenchTaskEventPayload:
    return WorkbenchTaskEventPayload(
        sequence=event.sequence,
        event_type=event.event_type,
        created_at=event.created_at,
        status=event.status,
        message=event.message,
        metadata=dict(event.metadata or {}),
    )


def _to_source_payload(source: WorkbenchSourceDescriptor) -> WorkbenchSourcePayload:
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


def create_workbench_task(
    *,
    request: WorkbenchTaskRequest,
    repository: WorkbenchTaskRepository,
    settings: Settings,
    auth_context: AuthorizationContext,
) -> WorkbenchTaskAcceptedResponse:
    """Create one durable queued workbench task."""
    ensure_agent_workbench_enabled(settings)
    now = _utc_now()
    requested_source_ids = normalize_requested_source_ids(
        source_ids=request.source_ids,
        connector_ids=request.connector_ids,
        knowledge_document_ids=request.knowledge_document_ids,
    )
    try:
        resolved_sources = resolve_requested_sources(
            source_ids=requested_source_ids,
            settings=settings,
            auth_context=auth_context,
        )
    except ValueError as exc:
        raise WorkbenchSourceValidationError(str(exc)) from exc
    if request.task_kind in {"browse", "deep_research"} and not any(
        source.runtime_ready for source in resolved_sources
    ):
        raise WorkbenchSourceValidationError(
            "At least one runtime-ready retrieval source is required for this task kind."
        )
    task = repository.create_task(
        WorkbenchTaskCreatePayload(
            task_id=f"wb-{uuid4().hex}",
            task_kind=request.task_kind,
            prompt=request.prompt,
            session_id=request.session_id,
            project_id=request.project_id,
            knowledge_document_ids=list(request.knowledge_document_ids),
            connector_ids=list(request.connector_ids),
            source_ids=[source.source_id for source in resolved_sources],
            created_at=now,
            updated_at=now,
            owner_id=auth_context.legacy_owner_id,
            tenant_id=auth_context.tenant_id.value,
            principal_id=auth_context.principal_id.value,
            auth_scopes=sorted(auth_context.scopes),
            credential_id=auth_context.credential_id,
            auth_mode=auth_context.auth_mode,
        )
    )
    return _to_accepted_response(task)


def create_and_dispatch_workbench_task(
    *,
    request: WorkbenchTaskRequest,
    repository: WorkbenchTaskRepository,
    dispatcher: WorkbenchTaskDispatcher,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str = "",
) -> WorkbenchTaskAcceptedResponse:
    """Create one durable workbench task and hand it to the runtime dispatcher."""
    accepted = create_workbench_task(
        request=request,
        repository=repository,
        settings=settings,
        auth_context=auth_context,
    )
    dispatcher.dispatch_task(task_id=accepted.task_id, request_id=request_id)
    return accepted


def get_workbench_task(
    *,
    task_id: str,
    repository: WorkbenchTaskRepository,
    settings: Settings,
    auth_context: AuthorizationContext,
) -> WorkbenchTaskStatusResponse:
    """Return one durable workbench task status when visible to the caller."""
    ensure_agent_workbench_enabled(settings)
    task = repository.get_task(task_id)
    if task is None:
        raise WorkbenchTaskNotFoundError("Workbench task not found")
    decision = authorize_workbench_task_read(
        ctx=auth_context,
        task=task,
        require_owner_header=settings.require_session_owner,
    )
    if not decision.allowed:
        raise WorkbenchTaskNotFoundError("Workbench task not found")
    response = _to_status_response(task)
    response.workspace_outputs = [
        _to_workspace_output_payload(output)
        for output in repository.list_workspace_outputs(task.id)
    ]
    return response


def get_workbench_task_events(
    *,
    task_id: str,
    repository: WorkbenchTaskRepository,
    settings: Settings,
    auth_context: AuthorizationContext,
) -> WorkbenchTaskEventsResponse:
    """Return the durable event timeline for one visible workbench task."""
    ensure_agent_workbench_enabled(settings)
    task = repository.get_task(task_id)
    if task is None:
        raise WorkbenchTaskNotFoundError("Workbench task not found")
    decision = authorize_workbench_task_read(
        ctx=auth_context,
        task=task,
        require_owner_header=settings.require_session_owner,
    )
    if not decision.allowed:
        raise WorkbenchTaskNotFoundError("Workbench task not found")
    return WorkbenchTaskEventsResponse(
        task_id=task.id,
        events=[
            _to_event_payload(event) for event in repository.list_task_events(task.id)
        ],
    )


def get_workbench_sources(
    *,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str = "",
) -> WorkbenchSourcesResponse:
    """Return the visible retrieval-source registry for workbench tasks."""
    ensure_agent_workbench_enabled(settings)
    return WorkbenchSourcesResponse(
        sources=[
            _to_source_payload(source)
            for source in list_workbench_sources(
                settings=settings,
                auth_context=auth_context,
                request_id=request_id,
            )
        ]
    )
