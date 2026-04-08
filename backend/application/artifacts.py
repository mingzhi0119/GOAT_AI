"""Artifact download use cases."""
from __future__ import annotations

from pathlib import Path

from fastapi.responses import FileResponse

from backend.application.ports import ArtifactNotFound, SessionRepository, Settings
from backend.services.artifact_service import load_artifact_for_download


def download_artifact_response(
    *,
    artifact_id: str,
    repository: SessionRepository,
    settings: Settings,
    request_owner: str,
) -> FileResponse:
    """Return a download response for one persisted artifact."""
    record = load_artifact_for_download(
        artifact_id=artifact_id,
        settings=settings,
        request_owner=request_owner,
        get_artifact=repository.get_chat_artifact,
    )
    path = Path(record.storage_path)
    if not path.is_file():
        raise ArtifactNotFound("Chat artifact not found.")
    return FileResponse(
        path=path,
        media_type=record.mime_type,
        filename=record.filename,
    )
