"""Persist and validate user image uploads for vision-capable chat.

Router layer reads multipart bytes; this module stays free of FastAPI imports.
"""

from __future__ import annotations

import base64
import re
import struct
from pathlib import Path
from uuid import uuid4

from backend.models.media import MediaUploadResponse
from backend.services.exceptions import MediaNotFound, MediaValidationError
from backend.types import Settings

_ATT_ID_RE = re.compile(r"^att-[a-f0-9]{32}$")


def _attachment_dir(settings: Settings, attachment_id: str) -> Path:
    return settings.data_dir / "uploads" / "media" / attachment_id


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
    base = _attachment_dir(settings, attachment_id)
    base.mkdir(parents=True, exist_ok=True)
    target = base / "image.bin"
    target.write_bytes(content)

    orig_name = filename.strip() or "image"
    meta = base / "meta.txt"
    meta.write_text(
        f"filename={orig_name}\nkind={kind}\n",
        encoding="utf-8",
    )

    return MediaUploadResponse(
        attachment_id=attachment_id,
        filename=orig_name,
        mime_type=f"image/{kind}" if kind != "jpeg" else "image/jpeg",
        byte_size=len(content),
        width_px=width_px,
        height_px=height_px,
    )


def load_normalized_base64_for_ollama(*, attachment_id: str, settings: Settings) -> str:
    """Return base64-encoded image bytes for one attachment (Ollama ``images`` field)."""
    if not _ATT_ID_RE.match(attachment_id):
        raise MediaNotFound("Image attachment not found.")
    path = _attachment_dir(settings, attachment_id) / "image.bin"
    if not path.is_file():
        raise MediaNotFound("Image attachment not found.")
    data = path.read_bytes()
    return base64.b64encode(data).decode("ascii")


def load_images_base64_for_chat(
    *, attachment_ids: list[str], settings: Settings
) -> list[str]:
    """Load multiple attachments in request order."""
    out: list[str] = []
    for aid in attachment_ids:
        out.append(
            load_normalized_base64_for_ollama(
                attachment_id=aid.strip(), settings=settings
            )
        )
    return out
