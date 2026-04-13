from __future__ import annotations

from pathlib import Path


def artifact_object_key(*, artifact_id: str, filename: str) -> str:
    safe_name = Path(filename).name or "artifact.bin"
    return f"artifacts/{artifact_id}/{safe_name}"


def media_object_key(*, attachment_id: str) -> str:
    return f"media/{attachment_id}/image.bin"


def knowledge_source_object_key(*, document_id: str, extension: str) -> str:
    normalized_extension = extension.lstrip(".").lower()
    return f"knowledge/{document_id}/original/source.{normalized_extension}"


def knowledge_normalized_text_object_key(*, document_id: str) -> str:
    return f"knowledge/{document_id}/normalized/extracted.txt"


def knowledge_normalized_metadata_object_key(*, document_id: str) -> str:
    return f"knowledge/{document_id}/normalized/metadata.json"


def knowledge_vector_index_prefix(*, backend_name: str) -> str:
    return f"vector-index/{backend_name}"


def knowledge_vector_index_object_key(*, backend_name: str, document_id: str) -> str:
    return (
        f"{knowledge_vector_index_prefix(backend_name=backend_name)}/{document_id}.json"
    )
