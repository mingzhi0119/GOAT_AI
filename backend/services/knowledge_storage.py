from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from goat_ai.config.settings import Settings

from backend.types import AsyncUploadReader


SUPPORTED_KNOWLEDGE_EXTENSIONS: frozenset[str] = frozenset(
    {"csv", "xlsx", "txt", "md", "pdf", "docx"}
)


class KnowledgeValidationError(ValueError):
    """Raised when a knowledge upload is invalid at the API boundary."""


@dataclass(frozen=True)
class StoredKnowledgeFile:
    document_id: str
    filename: str
    mime_type: str
    byte_size: int
    sha256: str
    storage_path: Path


def _extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def knowledge_document_dir(settings: Settings, document_id: str) -> Path:
    return settings.data_dir / "uploads" / "knowledge" / document_id


def knowledge_vector_dir(settings: Settings, backend_name: str) -> Path:
    return settings.data_dir / "vector_index" / backend_name


async def persist_knowledge_upload(
    *,
    file: AsyncUploadReader,
    settings: Settings,
    document_id: str,
    max_read_bytes: int,
) -> StoredKnowledgeFile:
    if not file.filename:
        raise KnowledgeValidationError("No filename provided.")
    content = await file.read(max_read_bytes)
    return persist_knowledge_bytes(
        content=content,
        filename=file.filename,
        content_type=file.content_type,
        settings=settings,
        document_id=document_id,
    )


def persist_knowledge_bytes(
    *,
    content: bytes,
    filename: str,
    content_type: str | None,
    settings: Settings,
    document_id: str,
) -> StoredKnowledgeFile:
    ext = _extension(filename)
    if ext not in SUPPORTED_KNOWLEDGE_EXTENSIONS:
        raise KnowledgeValidationError(
            "Supported knowledge upload types are CSV, XLSX, TXT, MD, PDF, and DOCX."
        )
    if not content:
        raise KnowledgeValidationError("Uploaded file is empty.")

    document_dir = knowledge_document_dir(settings, document_id)
    original_dir = document_dir / "original"
    original_dir.mkdir(parents=True, exist_ok=True)
    storage_path = original_dir / f"source.{ext}"
    storage_path.write_bytes(content)
    mime_type = content_type or "application/octet-stream"
    digest = hashlib.sha256(content).hexdigest()
    return StoredKnowledgeFile(
        document_id=document_id,
        filename=filename,
        mime_type=mime_type,
        byte_size=len(content),
        sha256=digest,
        storage_path=storage_path,
    )
