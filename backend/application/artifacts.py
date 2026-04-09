"""Artifact download use cases."""

from __future__ import annotations

from pathlib import Path

from fastapi.responses import FileResponse

from backend.domain.authz_types import AuthorizationContext
from backend.services.authorizer import authorize_artifact_read
from backend.application.ports import ArtifactNotFound, SessionRepository, Settings
from backend.domain.authorization import ResourceRef
from backend.services.artifact_service import load_artifact_for_download
from backend.services.authz_audit import emit_authorization_audit


def download_artifact_response(
    *,
    artifact_id: str,
    repository: SessionRepository,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str,
) -> FileResponse:
    """Return a download response for one persisted artifact."""
    record = load_artifact_for_download(
        artifact_id=artifact_id,
        settings=settings,
        request_owner=auth_context.legacy_owner_id,
        get_artifact=repository.get_chat_artifact,
    )
    decision = authorize_artifact_read(
        ctx=auth_context,
        artifact=record,
        require_owner_header=settings.require_session_owner,
    )
    emit_authorization_audit(
        ctx=auth_context,
        action="artifact.read",
        resource=ResourceRef(resource_type="artifact", resource_id=artifact_id),
        decision=decision,
        request_id=request_id,
    )
    if not decision.allowed:
        raise ArtifactNotFound("Chat artifact not found.")
    path = Path(record.storage_path)
    if not path.is_file():
        raise ArtifactNotFound("Chat artifact not found.")
    return FileResponse(
        path=path,
        media_type=record.mime_type,
        filename=record.filename,
    )
