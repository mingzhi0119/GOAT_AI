"""Compatibility shim for the canonical object-store implementation.

New code should import from ``goat_ai.uploads`` or ``goat_ai.uploads.object_store``.
This module stays as a narrow alias surface so older imports keep working while the
Phase 16 object-storage boundary converges on one implementation.
"""

from __future__ import annotations

from pathlib import Path

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


class FilesystemObjectStore(LocalObjectStore):
    def __init__(self, root: Path) -> None:
        super().__init__(root=root, allowed_absolute_roots=(root,))


ObjectStorageError = ObjectStoreError
ObjectStorageNotFoundError = ObjectNotFoundError
normalize_storage_key = normalize_object_key
normalize_storage_prefix = normalize_object_prefix

__all__ = [
    "FilesystemObjectStore",
    "LocalObjectStore",
    "ObjectNotFoundError",
    "ObjectStorageError",
    "ObjectStorageNotFoundError",
    "ObjectStore",
    "ObjectStoreError",
    "S3ObjectStore",
    "StoredObjectDescriptor",
    "build_object_store",
    "normalize_object_key",
    "normalize_object_prefix",
    "normalize_storage_key",
    "normalize_storage_prefix",
    "read_text",
    "write_text",
]
