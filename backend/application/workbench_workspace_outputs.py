"""Workbench workspace output and export entrypoints."""

from __future__ import annotations

from backend.application.exceptions import (
    WorkbenchPermissionDeniedError,
    WorkbenchWorkspaceOutputNotFoundError,
)
from backend.application.ports import (
    SessionRepository,
    Settings,
    WorkbenchTaskRepository,
)
from backend.application.workbench_shared import (
    ensure_agent_workbench_enabled,
    filter_visible_workspace_outputs,
    load_visible_workspace_output,
    to_workspace_output_payload,
    utc_now,
)
from backend.domain.authz_types import AuthorizationContext
from backend.models.artifact import ChatArtifact
from backend.models.workbench import (
    WorkbenchWorkspaceOutputExportRequest,
    WorkbenchWorkspaceOutputPayload,
    WorkbenchWorkspaceOutputsResponse,
)
from backend.services.artifact_service import (
    artifact_to_wire,
    persist_artifact,
    prepare_export_artifact,
)
from backend.services.authorizer import (
    authorize_workbench_output_export,
    workbench_read_policy_allowed,
)


def get_workbench_workspace_output(
    *,
    output_id: str,
    repository: WorkbenchTaskRepository,
    settings: Settings,
    auth_context: AuthorizationContext,
) -> WorkbenchWorkspaceOutputPayload:
    """Return one durable workspace output when visible to the caller."""
    output = load_visible_workspace_output(
        output_id=output_id,
        repository=repository,
        settings=settings,
        auth_context=auth_context,
    )
    return to_workspace_output_payload(output)


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
        outputs=filter_visible_workspace_outputs(
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
    now = utc_now()
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
