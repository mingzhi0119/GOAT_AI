"""Shared request-boundary helpers for upload endpoints."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class UploadFileLike(Protocol):
    """Minimal async upload interface required by request parsing."""

    filename: str | None

    async def read(self, size: int = -1) -> bytes:
        ...


class UploadValidationError(ValueError):
    """Raised when upload metadata or extension is invalid at request boundary."""


@dataclass(frozen=True)
class UploadRequestPayload:
    """Validated upload metadata and bytes extracted from a request file."""

    filename: str
    content: bytes


async def read_validated_upload(
    *,
    file: UploadFileLike,
    max_read_bytes: int,
) -> UploadRequestPayload:
    """Validate an uploaded CSV/XLSX file and return its raw bytes."""
    if not file.filename:
        raise UploadValidationError("No filename provided.")

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ("csv", "xlsx"):
        raise UploadValidationError("Only CSV and XLSX files are supported.")

    content = await file.read(max_read_bytes)
    return UploadRequestPayload(filename=file.filename, content=content)
