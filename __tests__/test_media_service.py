from __future__ import annotations

import base64
import tempfile
import unittest
from pathlib import Path

from backend.domain.authz_types import AuthorizationContext
from backend.domain.authorization import PrincipalId, TenantId
from backend.services import log_service
from backend.services.exceptions import MediaNotFound, MediaValidationError
from backend.services.media_service import (
    MediaUploadRecord,
    create_media_upload_from_bytes,
    load_images_base64_for_chat,
    load_normalized_base64_for_ollama,
)
from goat_ai.config import Settings

PNG_1X1_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7Z0ioAAAAASUVORK5CYII="


def _auth_context(
    *,
    owner_id: str = "owner-1",
    tenant_id: str = "tenant-1",
    principal_id: str = "principal-1",
) -> AuthorizationContext:
    return AuthorizationContext(
        principal_id=PrincipalId(principal_id),
        tenant_id=TenantId(tenant_id),
        scopes=frozenset({"media:read", "media:write"}),
        credential_id="cred-1",
        legacy_owner_id=owner_id,
        auth_mode="api_key",
    )


class MediaServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        root = Path(self.tmpdir.name)
        self.settings = Settings(
            ollama_base_url="http://127.0.0.1:11434",
            generate_timeout=120,
            max_upload_mb=20,
            max_upload_bytes=20 * 1024 * 1024,
            max_dataframe_rows=50000,
            use_chat_api=True,
            system_prompt="test",
            app_root=root,
            logo_svg=root / "logo.svg",
            log_db_path=root / "chat_logs.db",
            data_dir=root / "data",
        )
        log_service.init_db(self.settings.log_db_path)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_create_media_upload_persists_png_and_reads_base64(self) -> None:
        content = base64.b64decode(PNG_1X1_BASE64)

        response = create_media_upload_from_bytes(
            content=content,
            filename="pixel.png",
            settings=self.settings,
            auth_context=_auth_context(),
            request_id="req-1",
        )

        self.assertTrue(response.attachment_id.startswith("att-"))
        self.assertEqual("image/png", response.mime_type)
        self.assertEqual(1, response.width_px)
        self.assertEqual(1, response.height_px)

        encoded = load_normalized_base64_for_ollama(
            attachment_id=response.attachment_id,
            settings=self.settings,
            auth_context=_auth_context(),
            request_id="req-2",
        )

        self.assertEqual(content, base64.b64decode(encoded))

    def test_create_media_upload_rejects_unsupported_bytes(self) -> None:
        with self.assertRaises(MediaValidationError):
            create_media_upload_from_bytes(
                content=b"not-an-image",
                filename="notes.txt",
                settings=self.settings,
                auth_context=_auth_context(),
            )

    def test_load_media_rejects_invalid_attachment_id(self) -> None:
        with self.assertRaises(MediaNotFound):
            load_normalized_base64_for_ollama(
                attachment_id="bad-id",
                settings=self.settings,
                auth_context=_auth_context(),
            )

    def test_load_media_conceals_unauthorized_attachment(self) -> None:
        content = base64.b64decode(PNG_1X1_BASE64)
        response = create_media_upload_from_bytes(
            content=content,
            filename="pixel.png",
            settings=self.settings,
            auth_context=_auth_context(principal_id="principal-1"),
        )

        with self.assertRaises(MediaNotFound):
            load_normalized_base64_for_ollama(
                attachment_id=response.attachment_id,
                settings=self.settings,
                auth_context=_auth_context(principal_id="principal-2"),
            )

    def test_media_service_accepts_injected_repository(self) -> None:
        content = base64.b64decode(PNG_1X1_BASE64)
        root = self.settings.data_dir

        class FakeMediaRepository:
            def __init__(self) -> None:
                self.records: dict[str, MediaUploadRecord] = {}

            def create_media_upload(self, record: MediaUploadRecord) -> None:
                self.records[record.id] = record

            def get_media_upload(self, attachment_id: str) -> MediaUploadRecord | None:
                return self.records.get(attachment_id)

        repository = FakeMediaRepository()

        response = create_media_upload_from_bytes(
            content=content,
            filename="pixel.png",
            settings=self.settings,
            auth_context=_auth_context(),
            repository=repository,
        )

        stored = repository.get_media_upload(response.attachment_id)
        self.assertIsNotNone(stored)
        assert stored is not None
        self.assertTrue(Path(stored.storage_path).is_file())
        self.assertTrue(str(Path(stored.storage_path)).startswith(str(root)))

        encoded_images = load_images_base64_for_chat(
            attachment_ids=[response.attachment_id],
            settings=self.settings,
            auth_context=_auth_context(),
            repository=repository,
        )

        self.assertEqual([content], [base64.b64decode(item) for item in encoded_images])


if __name__ == "__main__":
    unittest.main()
