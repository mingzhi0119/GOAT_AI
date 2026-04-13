from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

import goat_ai.uploads.object_store as object_store_module
from goat_ai.uploads import (
    LocalObjectStore,
    ObjectNotFoundError,
    S3ObjectStore,
    normalize_object_key,
)


class _FakeClientError(object_store_module.ClientError):
    def __init__(self, code: str) -> None:
        super().__init__({"Error": {"Code": code}}, "fake-operation")
        self.response = {"Error": {"Code": code}}


class _FakeS3Client:
    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    def put_object(self, **params: object) -> None:
        self._objects[str(params["Key"])] = bytes(params["Body"])

    def get_object(self, **params: object) -> dict[str, object]:
        key = str(params["Key"])
        if key not in self._objects:
            raise _FakeClientError("NoSuchKey")
        return {"Body": io.BytesIO(self._objects[key])}

    def head_object(self, **params: object) -> dict[str, object]:
        key = str(params["Key"])
        if key not in self._objects:
            raise _FakeClientError("NotFound")
        return {}

    def delete_object(self, **params: object) -> None:
        self._objects.pop(str(params["Key"]), None)

    def list_objects_v2(self, **params: object) -> dict[str, object]:
        prefix = str(params.get("Prefix", ""))
        return {
            "Contents": [
                {"Key": key} for key in sorted(self._objects) if key.startswith(prefix)
            ],
            "IsTruncated": False,
        }


class ObjectStorageTests(unittest.TestCase):
    def test_normalize_object_key_rejects_escape_attempts(self) -> None:
        with self.assertRaises(ValueError):
            normalize_object_key("../secrets.txt")
        with self.assertRaises(ValueError):
            normalize_object_key("/absolute/path.txt")

    def test_local_store_lists_reads_and_deletes_objects(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            root = Path(tmp) / "object-store"
            store = LocalObjectStore(root)

            descriptor = store.put_bytes(
                key="knowledge/doc-1/original/source.txt",
                content=b"hello",
            )

            self.assertEqual(
                ["knowledge/doc-1/original/source.txt"],
                store.list_keys(prefix="knowledge/doc-1"),
            )
            self.assertEqual(b"hello", store.read_bytes(descriptor.storage_key))
            self.assertEqual(5, descriptor.byte_size)
            self.assertTrue(bool(descriptor.sha256))
            self.assertIsNotNone(descriptor.filesystem_path)
            assert descriptor.filesystem_path is not None
            self.assertTrue(root in descriptor.filesystem_path.parents)

            store.delete(descriptor.storage_key)

            self.assertEqual([], store.list_keys(prefix="knowledge/doc-1"))
            with self.assertRaises(ObjectNotFoundError):
                store.read_bytes(descriptor.storage_key)

    def test_local_store_reads_legacy_absolute_paths_within_allowed_roots(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            root = Path(tmp) / "object-store"
            legacy_root = Path(tmp) / "legacy-data"
            legacy_root.mkdir(parents=True, exist_ok=True)
            legacy_path = legacy_root / "uploads" / "artifact.txt"
            legacy_path.parent.mkdir(parents=True, exist_ok=True)
            legacy_path.write_bytes(b"legacy")
            store = LocalObjectStore(root, allowed_absolute_roots=(root, legacy_root))

            self.assertEqual(b"legacy", store.read_bytes(str(legacy_path)))
            self.assertEqual(
                legacy_path.resolve(), store.get_filesystem_path(str(legacy_path))
            )

    def test_s3_store_round_trips_relative_keys_and_hides_filesystem_paths(
        self,
    ) -> None:
        store = S3ObjectStore(
            bucket="goat-test", prefix="tenant-a", client=_FakeS3Client()
        )

        descriptor = store.put_bytes(
            key="artifacts/art-1/report.txt",
            content=b"hello from s3",
            content_type="text/plain",
        )

        self.assertEqual("artifacts/art-1/report.txt", descriptor.storage_key)
        self.assertEqual(13, descriptor.byte_size)
        self.assertTrue(store.exists(descriptor.storage_key))
        self.assertEqual(b"hello from s3", store.read_bytes(descriptor.storage_key))
        self.assertEqual(
            ["artifacts/art-1/report.txt"],
            store.list_keys(prefix="artifacts"),
        )
        self.assertIsNone(store.get_filesystem_path(descriptor.storage_key))

        store.delete(descriptor.storage_key)

        self.assertFalse(store.exists(descriptor.storage_key))
        with self.assertRaises(ObjectNotFoundError):
            store.read_bytes(descriptor.storage_key)


if __name__ == "__main__":
    unittest.main()
