"""Artifact download use cases."""

from __future__ import annotations

from urllib.parse import quote
from pathlib import Path

from fastapi.responses import FileResponse, Response

from backend.domain.authz_types import AuthorizationContext
from backend.services.authorizer import authorize_artifact_read
from backend.application.ports import ArtifactNotFound, SessionRepository, Settings
from backend.domain.authorization import ResourceRef
from backend.services.artifact_service import (
    load_artifact_for_download,
    read_artifact_bytes,
)
from backend.services.authz_audit import emit_authorization_audit
from goat_ai.uploads import build_object_store


def download_artifact_response(
    *,
    artifact_id: str,
    repository: SessionRepository,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str,
) -> Response:
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
    if record.storage_key:
        path = build_object_store(settings).get_filesystem_path(record.storage_key)
        if path is not None and path.is_file():
            return FileResponse(
                path=path,
                media_type=record.mime_type,
                filename=record.filename,
            )
    path = Path(record.storage_path)
    if path.is_file():
        return FileResponse(
            path=path,
            media_type=record.mime_type,
            filename=record.filename,
        )
    data = read_artifact_bytes(record=record, settings=settings)
    return Response(
        content=data,
        media_type=record.mime_type,
        headers={
            "Content-Disposition": (
                f"attachment; filename*=UTF-8''{quote(record.filename)}"
            )
        },
    )
