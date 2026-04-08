from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backend.services.knowledge_pipeline import normalize_document
from goat_ai.config import Settings


class KnowledgePipelineNormalizationTests(unittest.TestCase):
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
            ready_skip_ollama_probe=True,
        )

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_normalize_document_reads_pdf_text(self) -> None:
        source_dir = self.settings.data_dir / "uploads" / "knowledge" / "doc-pdf" / "original"
        source_dir.mkdir(parents=True, exist_ok=True)
        source_path = source_dir / "source.pdf"
        source_path.write_bytes(b"%PDF-1.4")

        fake_reader = SimpleNamespace(
            pages=[
                SimpleNamespace(extract_text=lambda: "Page one"),
                SimpleNamespace(extract_text=lambda: "Page two"),
            ]
        )
        with patch("backend.services.knowledge_pipeline.PdfReader", return_value=fake_reader):
            text = normalize_document(
                settings=self.settings,
                document_id="doc-pdf",
                filename="report.pdf",
            )

        self.assertEqual("Page one\n\nPage two", text)

    def test_normalize_document_reads_docx_text(self) -> None:
        source_dir = self.settings.data_dir / "uploads" / "knowledge" / "doc-docx" / "original"
        source_dir.mkdir(parents=True, exist_ok=True)
        source_path = source_dir / "source.docx"
        source_path.write_bytes(b"docx")

        fake_document = SimpleNamespace(
            paragraphs=[
                SimpleNamespace(text="Executive summary"),
                SimpleNamespace(text=""),
                SimpleNamespace(text="Second paragraph"),
            ]
        )
        with patch("backend.services.knowledge_pipeline.DocxDocument", return_value=fake_document):
            text = normalize_document(
                settings=self.settings,
                document_id="doc-docx",
                filename="memo.docx",
            )

        self.assertEqual("Executive summary\n\nSecond paragraph", text)


if __name__ == "__main__":
    unittest.main()
