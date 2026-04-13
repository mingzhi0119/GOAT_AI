"""Persist and validate user image uploads for vision-capable chat.

Router layer reads multipart bytes; this module stays free of FastAPI imports.
"""

from __future__ import annotations

import base64
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
import struct
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from backend.domain.authz_types import AuthorizationContext
from backend.domain.resource_ownership import (
    PersistedResourceOwnership,
    ownership_from_fields,
)
from backend.services.authorizer import authorize_media_read
from backend.domain.authorization import ResourceRef
from backend.models.media import MediaUploadResponse
from backend.services.exceptions import MediaNotFound, MediaValidationError
from backend.services.authz_audit import emit_authorization_audit
from backend.types import Settings
from goat_ai.uploads import (
    ObjectStore,
    build_object_store,
    media_object_key,
)

_ATT_ID_RE = re.compile(r"^att-[a-f0-9]{32}$")


@dataclass(frozen=True)
class MediaUploadRecord:
    id: str
    owner_id: str
    tenant_id: str
    principal_id: str
    filename: str
    mime_type: str
    byte_size: int
    storage_path: str
    width_px: int | None
    height_px: int | None
    created_at: str
    storage_key: str = ""

    @property
    def ownership(self) -> PersistedResourceOwnership:
        return ownership_from_fields(
            owner_id=self.owner_id,
            tenant_id=self.tenant_id,
            principal_id=self.principal_id,
        )


class MediaRepository(Protocol):
    def create_media_upload(self, record: MediaUploadRecord) -> None: ...

    def get_media_upload(self, attachment_id: str) -> MediaUploadRecord | None: ...


class SQLiteMediaRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def create_media_upload(self, record: MediaUploadRecord) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO media_uploads
                    (id, owner_id, tenant_id, principal_id, filename, mime_type, byte_size, storage_path, storage_key, width_px, height_px, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.owner_id,
                    record.tenant_id,
                    record.principal_id,
                    record.filename,
                    record.mime_type,
                    record.byte_size,
                    record.storage_path,
                    record.storage_key,
                    record.width_px,
                    record.height_px,
                    record.created_at,
                ),
            )

    def get_media_upload(self, attachment_id: str) -> MediaUploadRecord | None:
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT id, owner_id, tenant_id, principal_id, filename, mime_type, byte_size, storage_path, storage_key, width_px, height_px, created_at
                FROM media_uploads
                WHERE id = ?
                """,
                (attachment_id,),
            ).fetchone()
        return MediaUploadRecord(**dict(row)) if row is not None else None


def media_storage_key(attachment_id: str, *, filename: str = "image.bin") -> str:
    _ = filename
    return media_object_key(attachment_id=attachment_id)


def media_metadata_storage_key(attachment_id: str) -> str:
    return f"uploads/media/{attachment_id}/meta.txt"


def _resolve_repository(
    *, settings: Settings, repository: MediaRepository | None
) -> MediaRepository:
    return repository or SQLiteMediaRepository(settings.log_db_path)


def _sniff_image_kind(data: bytes) -> str | None:
    if len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if len(data) >= 3 and data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def _png_dimensions(data: bytes) -> tuple[int, int] | None:
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    length = struct.unpack(">I", data[8:12])[0]
    if data[12:16] != b"IHDR" or length < 13:
        return None
    w, h = struct.unpack(">II", data[16:24])
    return (int(w), int(h))


def create_media_upload_from_bytes(
    *,
    content: bytes,
    filename: str,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str = "",
    repository: MediaRepository | None = None,
    object_store: ObjectStore | None = None,
) -> MediaUploadResponse:
    """Validate, persist, and register one image for later vision chat."""
    if not content:
        raise MediaValidationError("Empty upload.")
    if len(content) > settings.max_image_media_bytes:
        raise MediaValidationError(
            f"Image exceeds maximum size ({settings.max_image_media_bytes} bytes).",
        )

    kind = _sniff_image_kind(content)
    if kind is None:
        raise MediaValidationError("Unsupported image type (allowed: PNG, JPEG, WebP).")

    width_px: int | None = None
    height_px: int | None = None
    if kind == "png":
        dims = _png_dimensions(content)
        if dims is not None:
            width_px, height_px = dims

    attachment_id = f"att-{uuid4().hex}"
    orig_name = filename.strip() or "image"
    mime_type = f"image/{kind}" if kind != "jpeg" else "image/jpeg"
    metadata_key = media_metadata_storage_key(attachment_id)
    store = object_store or build_object_store(settings)
    stored = store.put_bytes(
        storage_key=media_storage_key(attachment_id),
        content=content,
    )
    store.put_bytes(
        storage_key=metadata_key,
        content=f"filename={orig_name}\nkind={kind}\n".encode("utf-8"),
    )
    record = MediaUploadRecord(
        id=attachment_id,
        owner_id=auth_context.legacy_owner_id,
        tenant_id=auth_context.tenant_id.value,
        principal_id=auth_context.principal_id.value,
        filename=orig_name,
        mime_type=mime_type,
        byte_size=len(content),
        storage_path=str(stored.filesystem_path or ""),
        storage_key=stored.storage_key,
        width_px=width_px,
        height_px=height_px,
        created_at=_now_iso(),
    )
    repository = _resolve_repository(settings=settings, repository=repository)
    try:
        repository.create_media_upload(record)
    except Exception:
        store.delete(stored.storage_key)
        store.delete(metadata_key)
        raise
    emit_authorization_audit(
        ctx=auth_context,
        action="media.upload.create",
        resource=ResourceRef(resource_type="media_upload", resource_id=attachment_id),
        decision=authorize_media_read(
            ctx=auth_context,
            media=record,
            require_owner_header=settings.require_session_owner,
        ),
        request_id=request_id,
    )

    return MediaUploadResponse(
        attachment_id=attachment_id,
        filename=orig_name,
        mime_type=mime_type,
        byte_size=len(content),
        width_px=width_px,
        height_px=height_px,
    )


def load_normalized_base64_for_ollama(
    *,
    attachment_id: str,
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str = "",
    repository: MediaRepository | None = None,
    object_store: ObjectStore | None = None,
) -> str:
    """Return base64-encoded image bytes for one attachment (Ollama ``images`` field)."""
    if not _ATT_ID_RE.match(attachment_id):
        raise MediaNotFound("Image attachment not found.")
    repository = _resolve_repository(settings=settings, repository=repository)
    record = repository.get_media_upload(attachment_id)
    if record is None:
        raise MediaNotFound("Image attachment not found.")
    decision = authorize_media_read(
        ctx=auth_context,
        media=record,
        require_owner_header=settings.require_session_owner,
    )
    emit_authorization_audit(
        ctx=auth_context,
        action="media.upload.read",
        resource=ResourceRef(resource_type="media_upload", resource_id=attachment_id),
        decision=decision,
        request_id=request_id,
    )
    if not decision.allowed:
        raise MediaNotFound("Image attachment not found.")
    data = read_media_bytes(
        record=record,
        settings=settings,
        object_store=object_store,
    )
    return base64.b64encode(data).decode("ascii")


def load_images_base64_for_chat(
    *,
    attachment_ids: list[str],
    settings: Settings,
    auth_context: AuthorizationContext,
    request_id: str = "",
    repository: MediaRepository | None = None,
    object_store: ObjectStore | None = None,
) -> list[str]:
    """Load multiple attachments in request order."""
    out: list[str] = []
    for aid in attachment_ids:
        out.append(
            load_normalized_base64_for_ollama(
                attachment_id=aid.strip(),
                settings=settings,
                auth_context=auth_context,
                request_id=request_id,
                repository=repository,
                object_store=object_store,
            )
        )
    return out


def read_media_bytes(
    *,
    record: MediaUploadRecord,
    settings: Settings,
    object_store: ObjectStore | None = None,
) -> bytes:
    if record.storage_key:
        store = object_store or build_object_store(settings)
        return store.read_bytes(record.storage_key)
    path = Path(record.storage_path)
    if not path.is_file():
        raise MediaNotFound("Image attachment not found.")
    return path.read_bytes()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
