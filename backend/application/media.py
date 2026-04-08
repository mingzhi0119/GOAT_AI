"""Media upload use cases for vision attachments."""
from __future__ import annotations

from backend.application.ports import Settings
from backend.models.media import MediaUploadResponse
from backend.services.media_service import create_media_upload_from_bytes


def create_media_upload(*, content: bytes, filename: str, settings: Settings) -> MediaUploadResponse:
    """Persist and normalize one vision image upload."""
    return create_media_upload_from_bytes(content=content, filename=filename, settings=settings)
