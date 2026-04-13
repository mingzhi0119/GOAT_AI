from __future__ import annotations

from goat_ai.uploads.object_keys import (
    artifact_object_key,
    knowledge_normalized_metadata_object_key,
    knowledge_normalized_text_object_key,
    knowledge_source_object_key,
    knowledge_vector_index_object_key,
    knowledge_vector_index_prefix,
    media_object_key,
)
from goat_ai.uploads.object_store import (
    LocalObjectStore,
    ObjectNotFoundError,
    ObjectStore,
    ObjectStoreError,
    S3ObjectStore,
    StoredObjectDescriptor,
    build_object_store,
    normalize_object_key,
    normalize_object_prefix,
    read_text,
    write_text,
)
from goat_ai.uploads.object_storage import (
    FilesystemObjectStore,
    ObjectStorageError,
    ObjectStorageNotFoundError,
    normalize_storage_key,
)

__all__ = [
    "LocalObjectStore",
    "FilesystemObjectStore",
    "ObjectNotFoundError",
    "ObjectStore",
    "ObjectStoreError",
    "ObjectStorageError",
    "ObjectStorageNotFoundError",
    "S3ObjectStore",
    "StoredObjectDescriptor",
    "artifact_object_key",
    "build_object_store",
    "knowledge_normalized_metadata_object_key",
    "knowledge_normalized_text_object_key",
    "knowledge_source_object_key",
    "knowledge_vector_index_object_key",
    "knowledge_vector_index_prefix",
    "media_object_key",
    "normalize_object_key",
    "normalize_object_prefix",
    "normalize_storage_key",
    "read_text",
    "write_text",
]
