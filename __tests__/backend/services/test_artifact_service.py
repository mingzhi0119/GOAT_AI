from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.services.artifact_service import (
    PreparedArtifact,
    persist_artifact,
    prepare_export_artifact,
)
from backend.services.exceptions import PersistenceWriteError
from goat_ai.config import Settings


class ArtifactServiceTests(unittest.TestCase):
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

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_persist_artifact_cleans_up_file_when_registry_write_fails(self) -> None:
        prepared = PreparedArtifact(
            filename="brief.md",
            mime_type="text/markdown",
            content=b"# brief",
        )

        def _raise_persistence_error(_: object) -> None:
            raise PersistenceWriteError("db down")

        with self.assertRaises(PersistenceWriteError):
            persist_artifact(
                prepared=prepared,
                settings=self.settings,
                session_id="sess-1",
                owner_id="",
                tenant_id="tenant:default",
                principal_id="",
                source_message_index=0,
                register_artifact=_raise_persistence_error,
            )

        artifacts_root = self.settings.data_dir / "uploads" / "artifacts"
        if artifacts_root.exists():
            self.assertEqual([], list(artifacts_root.rglob("*")))

    def test_prepare_export_artifact_derives_filename_from_title(self) -> None:
        prepared = prepare_export_artifact(
            title="Quarterly Draft",
            content_text="# Quarterly Draft\n\nBody",
            export_format="markdown",
        )

        self.assertEqual("quarterly-draft.md", prepared.filename)
        self.assertEqual("text/markdown", prepared.mime_type)
        self.assertEqual(b"# Quarterly Draft\n\nBody", prepared.content)

    def test_prepare_export_artifact_rejects_mismatched_extension(self) -> None:
        with self.assertRaisesRegex(ValueError, "extension must match"):
            prepare_export_artifact(
                title="Quarterly Draft",
                content_text="# Quarterly Draft\n\nBody",
                export_format="markdown",
                filename="quarterly.txt",
            )


if __name__ == "__main__":
    unittest.main()
