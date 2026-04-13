"""Workbench task lifecycle entrypoints."""

from __future__ import annotations

from uuid import uuid4

from backend.application.exceptions import (
    WorkbenchPermissionDeniedError,
    WorkbenchSourceValidationError,
    WorkbenchTaskConflictError,
)
from backend.application.ports import (
    Settings,
    WorkbenchTaskDispatcher,
    WorkbenchTaskRepository,
)
from backend.application.workbench_shared import (
    build_task_create_payload,
    ensure_agent_workbench_enabled,
    ensure_source_requirements,
    ensure_sources_support_task_kind,
    filter_visible_workspace_outputs,
    load_visible_task,
    to_accepted_response,
    to_event_payload,
    to_status_response,
    utc_now,
)
from backend.domain.authz_types import AuthorizationContext
from backend.models.workbench import (
    WorkbenchTaskAcceptedResponse,
    WorkbenchTaskEventsResponse,
    WorkbenchTaskRequest,
    WorkbenchTaskStatusResponse,
)
from backend.services.authorizer import workbench_write_policy_allowed
from backend.services.workbench_source_registry import (
    normalize_requested_source_ids,
    resolve_requested_sources,
)


def create_workbench_task(
    *,
    request: WorkbenchTaskRequest,
    repository: WorkbenchTaskRepository,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str = "",
) -> WorkbenchTaskAcceptedResponse:
    """Create one durable queued workbench task."""
    ensure_agent_workbench_enabled(settings)
    if not workbench_write_policy_allowed(auth_context):
        raise WorkbenchPermissionDeniedError(
            "Caller lacks the scopes required to create workbench tasks."
        )
    now = utc_now()
    requested_source_ids = normalize_requested_source_ids(
        source_ids=request.source_ids,
        connector_ids=request.connector_ids,
        knowledge_document_ids=request.knowledge_document_ids,
    )
    if request.task_kind in {"browse", "deep_research"} and not requested_source_ids:
        requested_source_ids.append("web")
    try:
        resolved_sources = resolve_requested_sources(
            source_ids=requested_source_ids,
            settings=settings,
            auth_context=auth_context,
            request_id=request_id,
        )
    except PermissionError as exc:
        raise WorkbenchPermissionDeniedError(str(exc)) from exc
    except ValueError as exc:
        raise WorkbenchSourceValidationError(str(exc)) from exc
    ensure_sources_support_task_kind(
        task_kind=request.task_kind,
        sources=resolved_sources,
    )
    ensure_source_requirements(
        project_id=request.project_id,
        sources=resolved_sources,
    )
    if request.task_kind in {"browse", "deep_research"} and not any(
        source.runtime_ready for source in resolved_sources
    ):
        raise WorkbenchSourceValidationError(
            "At least one runtime-ready retrieval source is required for this task kind."
        )
    task = repository.create_task(
        build_task_create_payload(
            task_id=f"wb-{uuid4().hex}",
            task_kind=request.task_kind,
            prompt=request.prompt,
            session_id=request.session_id,
            project_id=request.project_id,
            knowledge_document_ids=list(request.knowledge_document_ids),
            connector_ids=list(request.connector_ids),
            source_ids=[source.source_id for source in resolved_sources],
            created_at=now,
            owner_id=auth_context.legacy_owner_id,
            tenant_id=auth_context.tenant_id.value,
            principal_id=auth_context.principal_id.value,
            auth_scopes=sorted(auth_context.scopes),
            credential_id=auth_context.credential_id,
            auth_mode=auth_context.auth_mode,
        )
    )
    return to_accepted_response(task)


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
        request_id=request_id,
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
    task = load_visible_task(
        task_id=task_id,
        repository=repository,
        settings=settings,
        auth_context=auth_context,
    )
    response = to_status_response(task)
    response.workspace_outputs = filter_visible_workspace_outputs(
        outputs=repository.list_workspace_outputs(task.id),
        settings=settings,
        auth_context=auth_context,
    )
    return response


def cancel_workbench_task(
    *,
    task_id: str,
    repository: WorkbenchTaskRepository,
    settings: Settings,
    auth_context: AuthorizationContext,
) -> WorkbenchTaskStatusResponse:
    """Cancel one visible queued workbench task."""
    task = load_visible_task(
        task_id=task_id,
        repository=repository,
        settings=settings,
        auth_context=auth_context,
        access_mode="write",
    )
    if task.status != "queued":
        raise WorkbenchTaskConflictError(
            "Only queued workbench tasks can be cancelled."
        )
    repository.mark_task_cancelled(
        task.id,
        updated_at=utc_now(),
        error_detail="Task cancelled before execution.",
    )
    updated = repository.get_task(task.id)
    if updated is None:
        raise RuntimeError("Workbench task disappeared after cancellation.")
    response = to_status_response(updated)
    response.workspace_outputs = filter_visible_workspace_outputs(
        outputs=repository.list_workspace_outputs(updated.id),
        settings=settings,
        auth_context=auth_context,
    )
    return response


def retry_workbench_task(
    *,
    task_id: str,
    repository: WorkbenchTaskRepository,
    dispatcher: WorkbenchTaskDispatcher,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str = "",
) -> WorkbenchTaskAcceptedResponse:
    """Retry one visible terminal workbench task as a new queued task."""
    task = load_visible_task(
        task_id=task_id,
        repository=repository,
        settings=settings,
        auth_context=auth_context,
        access_mode="write",
    )
    if task.status not in {"completed", "failed", "cancelled"}:
        raise WorkbenchTaskConflictError(
            "Only terminal workbench tasks can be retried."
        )
    try:
        resolved_sources = resolve_requested_sources(
            source_ids=task.source_ids,
            settings=settings,
            auth_context=auth_context,
            request_id=request_id,
        )
    except PermissionError as exc:
        raise WorkbenchPermissionDeniedError(str(exc)) from exc
    except ValueError as exc:
        raise WorkbenchSourceValidationError(str(exc)) from exc
    ensure_sources_support_task_kind(
        task_kind=task.task_kind,
        sources=resolved_sources,
    )
    ensure_source_requirements(
        project_id=task.project_id,
        sources=resolved_sources,
    )
    now = utc_now()
    retried = repository.create_task(
        build_task_create_payload(
            task_id=f"wb-{uuid4().hex}",
            task_kind=task.task_kind,
            prompt=task.prompt,
            session_id=task.session_id,
            project_id=task.project_id,
            knowledge_document_ids=task.knowledge_document_ids,
            connector_ids=task.connector_ids,
            source_ids=[source.source_id for source in resolved_sources],
            created_at=now,
            owner_id=auth_context.legacy_owner_id,
            tenant_id=auth_context.tenant_id.value,
            principal_id=auth_context.principal_id.value,
            auth_scopes=sorted(auth_context.scopes),
            credential_id=auth_context.credential_id,
            auth_mode=auth_context.auth_mode,
        )
    )
    repository.append_task_event(
        task.id,
        event_type="task.retry_requested",
        created_at=now,
        status=task.status,
        message="Retry requested.",
        metadata={"retry_task_id": retried.id},
    )
    repository.append_task_event(
        retried.id,
        event_type="task.retry_created",
        created_at=now,
        status="queued",
        message="Task created from retry.",
        metadata={"source_task_id": task.id},
    )
    dispatcher.dispatch_task(task_id=retried.id, request_id=request_id)
    return to_accepted_response(retried)


def get_workbench_task_events(
    *,
    task_id: str,
    repository: WorkbenchTaskRepository,
    settings: Settings,
    auth_context: AuthorizationContext,
) -> WorkbenchTaskEventsResponse:
    """Return the durable event timeline for one visible workbench task."""
    task = load_visible_task(
        task_id=task_id,
        repository=repository,
        settings=settings,
        auth_context=auth_context,
    )
    return WorkbenchTaskEventsResponse(
        task_id=task.id,
        events=[
            to_event_payload(event) for event in repository.list_task_events(task.id)
        ],
    )
