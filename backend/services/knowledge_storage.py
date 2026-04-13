from __future__ import annotations

import hashlib
from dataclasses import dataclass
from goat_ai.config.settings import Settings
from goat_ai.uploads import (
    ObjectStore,
    StoredObjectDescriptor,
    build_object_store,
    knowledge_normalized_metadata_object_key,
    knowledge_normalized_text_object_key,
    knowledge_source_object_key,
    knowledge_vector_index_object_key,
)

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
    storage_path: str
    storage_key: str


def _extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def knowledge_original_storage_key(document_id: str, ext: str) -> str:
    return knowledge_source_object_key(document_id=document_id, extension=ext)


def knowledge_normalized_text_storage_key(document_id: str) -> str:
    return knowledge_normalized_text_object_key(document_id=document_id)


def knowledge_normalized_metadata_storage_key(document_id: str) -> str:
    return knowledge_normalized_metadata_object_key(document_id=document_id)


def knowledge_vector_storage_key(document_id: str, backend_name: str) -> str:
    return knowledge_vector_index_object_key(
        backend_name=backend_name,
        document_id=document_id,
    )


async def persist_knowledge_upload(
    *,
    file: AsyncUploadReader,
    settings: Settings,
    document_id: str,
    max_read_bytes: int,
    object_store: ObjectStore | None = None,
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
        object_store=object_store,
    )


def persist_knowledge_bytes(
    *,
    content: bytes,
    filename: str,
    content_type: str | None,
    settings: Settings,
    document_id: str,
    object_store: ObjectStore | None = None,
) -> StoredKnowledgeFile:
    ext = _extension(filename)
    if ext not in SUPPORTED_KNOWLEDGE_EXTENSIONS:
        raise KnowledgeValidationError(
            "Supported knowledge upload types are CSV, XLSX, TXT, MD, PDF, and DOCX."
        )
    if not content:
        raise KnowledgeValidationError("Uploaded file is empty.")

    store = object_store or build_object_store(settings)
    target_key = knowledge_original_storage_key(document_id, ext)
    stored = store.put_bytes(storage_key=target_key, content=content)
    mime_type = content_type or "application/octet-stream"
    digest = hashlib.sha256(content).hexdigest()
    return StoredKnowledgeFile(
        document_id=document_id,
        filename=filename,
        mime_type=mime_type,
        byte_size=len(content),
        sha256=digest,
        storage_path=str(stored.filesystem_path or ""),
        storage_key=stored.storage_key,
    )


def write_text_object(
    *,
    settings: Settings,
    storage_key: str,
    text: str,
    object_store: ObjectStore | None = None,
) -> StoredObjectDescriptor:
    store = object_store or build_object_store(settings)
    return store.put_bytes(storage_key=storage_key, content=text.encode("utf-8"))
