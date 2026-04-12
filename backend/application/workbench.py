"""Workbench task entrypoints."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from backend.application.exceptions import (
    WorkbenchPermissionDeniedError,
    WorkbenchSourceValidationError,
    WorkbenchTaskConflictError,
    WorkbenchTaskNotFoundError,
    WorkbenchWorkspaceOutputNotFoundError,
)
from backend.application.ports import (
    SessionRepository,
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
    WorkbenchWorkspaceOutputExportRequest,
    WorkbenchWorkspaceOutputPayload,
    WorkbenchWorkspaceOutputsResponse,
    WorkbenchSourcePayload,
    WorkbenchSourcesResponse,
    WorkbenchTaskStatusResponse,
)
from backend.models.artifact import ChatArtifact
from backend.models.knowledge import KnowledgeCitation
from backend.services.authorizer import (
    authorize_workbench_output_export,
    authorize_workbench_output_read,
    authorize_workbench_task_read,
    authorize_workbench_task_write,
    workbench_read_policy_allowed,
    workbench_write_policy_allowed,
)
from backend.services.artifact_service import (
    artifact_to_wire,
    persist_artifact,
    prepare_export_artifact,
)
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


def _filter_visible_workspace_outputs(
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
            visible.append(_to_workspace_output_payload(output))
    return visible


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


def _build_task_create_payload(
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


def _load_visible_task(
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
    now = _utc_now()
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
    if request.task_kind in {"browse", "deep_research"} and not any(
        source.runtime_ready for source in resolved_sources
    ):
        raise WorkbenchSourceValidationError(
            "At least one runtime-ready retrieval source is required for this task kind."
        )
    task = repository.create_task(
        _build_task_create_payload(
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
    task = _load_visible_task(
        task_id=task_id,
        repository=repository,
        settings=settings,
        auth_context=auth_context,
    )
    response = _to_status_response(task)
    response.workspace_outputs = [
        _to_workspace_output_payload(output)
        for output in repository.list_workspace_outputs(task.id)
    ]
    return response


def cancel_workbench_task(
    *,
    task_id: str,
    repository: WorkbenchTaskRepository,
    settings: Settings,
    auth_context: AuthorizationContext,
) -> WorkbenchTaskStatusResponse:
    """Cancel one visible queued workbench task."""
    task = _load_visible_task(
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
        updated_at=_utc_now(),
        error_detail="Task cancelled before execution.",
    )
    updated = repository.get_task(task.id)
    if updated is None:
        raise RuntimeError("Workbench task disappeared after cancellation.")
    response = _to_status_response(updated)
    response.workspace_outputs = [
        _to_workspace_output_payload(output)
        for output in repository.list_workspace_outputs(updated.id)
    ]
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
    task = _load_visible_task(
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
    now = _utc_now()
    retried = repository.create_task(
        _build_task_create_payload(
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
    return _to_accepted_response(retried)


def get_workbench_task_events(
    *,
    task_id: str,
    repository: WorkbenchTaskRepository,
    settings: Settings,
    auth_context: AuthorizationContext,
) -> WorkbenchTaskEventsResponse:
    """Return the durable event timeline for one visible workbench task."""
    task = _load_visible_task(
        task_id=task_id,
        repository=repository,
        settings=settings,
        auth_context=auth_context,
    )
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
    if not workbench_read_policy_allowed(auth_context):
        raise WorkbenchPermissionDeniedError(
            "Caller lacks the scopes required to read workbench sources."
        )
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


def get_workbench_workspace_output(
    *,
    output_id: str,
    repository: WorkbenchTaskRepository,
    settings: Settings,
    auth_context: AuthorizationContext,
) -> WorkbenchWorkspaceOutputPayload:
    """Return one durable workspace output when visible to the caller."""
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
    return _to_workspace_output_payload(output)


def list_workbench_workspace_outputs(
    *,
    repository: WorkbenchTaskRepository,
    settings: Settings,
    auth_context: AuthorizationContext,
    session_id: str | None = None,
    project_id: str | None = None,
) -> WorkbenchWorkspaceOutputsResponse:
    """List durable workspace outputs that can be restored by session or project."""
    ensure_agent_workbench_enabled(settings)
    if not workbench_read_policy_allowed(auth_context):
        raise WorkbenchPermissionDeniedError(
            "Caller lacks the scopes required to list workbench outputs."
        )
    if session_id and project_id:
        raise ValueError("Provide either session_id or project_id, not both.")
    if session_id:
        outputs = repository.list_workspace_outputs_for_session(session_id)
    elif project_id:
        outputs = repository.list_workspace_outputs_for_project(project_id)
    else:
        raise ValueError("Provide session_id or project_id.")
    return WorkbenchWorkspaceOutputsResponse(
        outputs=_filter_visible_workspace_outputs(
            outputs=outputs,
            settings=settings,
            auth_context=auth_context,
        )
    )


def export_workbench_workspace_output(
    *,
    output_id: str,
    request: WorkbenchWorkspaceOutputExportRequest,
    task_repository: WorkbenchTaskRepository,
    session_repository: SessionRepository,
    settings: Settings,
    auth_context: AuthorizationContext,
) -> ChatArtifact:
    """Export one durable workspace output into a downloadable artifact."""
    ensure_agent_workbench_enabled(settings)
    output = task_repository.get_workspace_output(output_id)
    if output is None:
        raise WorkbenchWorkspaceOutputNotFoundError(
            "Workbench workspace output not found"
        )
    export_decision = authorize_workbench_output_export(
        ctx=auth_context,
        output=output,
        require_owner_header=settings.require_session_owner,
    )
    if not export_decision.allowed:
        if export_decision.reason_code == "scope_missing":
            raise WorkbenchPermissionDeniedError(
                "Caller lacks the scopes required to export this workbench output."
            )
        raise WorkbenchWorkspaceOutputNotFoundError(
            "Workbench workspace output not found"
        )

    prepared = prepare_export_artifact(
        title=output.title,
        content_text=output.content_text,
        export_format=request.format,
        filename=request.filename,
    )
    record = persist_artifact(
        prepared=prepared,
        settings=settings,
        session_id=output.session_id or "",
        owner_id=output.owner_id,
        tenant_id=output.tenant_id,
        principal_id=output.principal_id,
        source_message_index=0,
        register_artifact=session_repository.create_chat_artifact,
    )
    linked_artifact = artifact_to_wire(record)
    existing_metadata = dict(output.metadata or {})
    existing_artifacts = [
        item
        for item in existing_metadata.get("artifacts", [])
        if isinstance(item, dict)
    ]
    existing_artifacts.append(linked_artifact.model_dump(mode="python"))
    existing_metadata["artifacts"] = existing_artifacts
    now = _utc_now()
    task_repository.replace_workspace_output_metadata(
        output.id,
        metadata=existing_metadata,
        updated_at=now,
    )
    task_repository.append_task_event(
        output.task_id,
        event_type="workspace_output.exported",
        created_at=now,
        status="completed",
        message=f"Workspace output {output.id} exported as artifact {record.id}.",
        metadata={
            "output_id": output.id,
            "artifact_id": record.id,
            "filename": record.filename,
            "mime_type": record.mime_type,
        },
    )
    return linked_artifact
