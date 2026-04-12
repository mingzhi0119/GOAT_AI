from __future__ import annotations

import unittest

from backend.services.upload_request_service import (
    UploadValidationError,
    read_validated_upload,
)


class _FakeUploadFile:
    def __init__(self, *, filename: str | None, content: bytes) -> None:
        self.filename = filename
        self._content = content

    async def read(self, size: int = -1) -> bytes:
        if size < 0:
            return self._content
        return self._content[:size]


class UploadRequestServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_reads_validated_csv_upload(self) -> None:
        payload = await read_validated_upload(
            file=_FakeUploadFile(filename="grades.csv", content=b"a,b\n1,2\n"),
            max_read_bytes=1024,
        )

        self.assertEqual("grades.csv", payload.filename)
        self.assertEqual(b"a,b\n1,2\n", payload.content)

    async def test_rejects_missing_filename(self) -> None:
        with self.assertRaises(UploadValidationError):
            await read_validated_upload(
                file=_FakeUploadFile(filename=None, content=b""),
                max_read_bytes=1024,
            )

    async def test_rejects_unsupported_extension(self) -> None:
        with self.assertRaises(UploadValidationError):
            await read_validated_upload(
                file=_FakeUploadFile(filename="notes.txt", content=b"hello"),
                max_read_bytes=1024,
            )


if __name__ == "__main__":
    unittest.main()
