"""Shared request-boundary helpers for upload endpoints."""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, UploadFile


@dataclass(frozen=True)
class UploadRequestPayload:
    """Validated upload metadata and bytes extracted from a request file."""

    filename: str
    content: bytes


async def read_validated_upload(
    *,
    file: UploadFile,
    max_read_bytes: int,
) -> UploadRequestPayload:
    """Validate an uploaded CSV/XLSX file and return its raw bytes."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ("csv", "xlsx"):
        raise HTTPException(status_code=400, detail="Only CSV and XLSX files are supported.")

    content = await file.read(max_read_bytes)
    return UploadRequestPayload(filename=file.filename, content=content)
