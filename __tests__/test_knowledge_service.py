from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.domain.authz_types import AuthorizationContext
from backend.domain.authorization import PrincipalId, TenantId
from backend.models.knowledge import (
    KnowledgeCitation,
    KnowledgeIngestionRequest,
)
from backend.services import knowledge_service, log_service
from backend.services.knowledge_repository import (
    KnowledgeChunkRow,
    KnowledgeDocumentRecord,
    SQLiteKnowledgeRepository,
)
from goat_ai.config import Settings


def _settings(root: Path) -> Settings:
    return Settings(
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
        require_session_owner=True,
    )


def _auth_context(owner_id: str = "owner-1") -> AuthorizationContext:
    return AuthorizationContext(
        principal_id=PrincipalId("principal-1"),
        tenant_id=TenantId("tenant-1"),
        scopes=frozenset({"knowledge:read", "knowledge:write"}),
        credential_id="cred-1",
        legacy_owner_id=owner_id,
        auth_mode="api_key",
    )


class KnowledgeServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.tmpdir.name)
        self.settings = _settings(self.root)
        log_service.init_db(self.settings.log_db_path)
        self.repository = SQLiteKnowledgeRepository(self.settings.log_db_path)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def _create_document(self, document_id: str, *, owner_id: str = "owner-1") -> None:
        now = "2026-04-11T00:00:00+00:00"
        self.repository.create_document(
            KnowledgeDocumentRecord(
                id=document_id,
                source_type="upload",
                original_filename=f"{document_id}.md",
                mime_type="text/markdown",
                sha256="abc",
                storage_path=str(self.root / f"{document_id}.md"),
                byte_size=12,
                status="uploaded",
                created_at=now,
                updated_at=now,
                deleted_at=None,
                owner_id=owner_id,
                tenant_id="tenant-1",
                principal_id="principal-1",
            )
        )

    def test_build_chat_context_falls_back_to_attached_document_chunks(self) -> None:
        self._create_document("doc-1")
        self.repository.replace_chunks(
            ingestion_id="ing-1",
            document_id="doc-1",
            chunks=[
                KnowledgeChunkRow(
                    id="chunk-1",
                    ingestion_id="ing-1",
                    document_id="doc-1",
                    chunk_index=0,
                    text_content="Fallback snippet from the attached document.",
                    text_hash="hash",
                    token_count=6,
                    char_start=0,
                    char_end=42,
                    vector_ref="doc-1:0",
                    created_at="2026-04-11T00:00:00+00:00",
                )
            ],
        )

        with patch(
            "backend.services.knowledge_service.search_vector_index", return_value=[]
        ):
            context = knowledge_service.build_chat_knowledge_context(
                query="Where is the fallback?",
                document_ids=["doc-1"],
                top_k=5,
                settings=self.settings,
                auth_context=_auth_context(),
            )

        self.assertIn("Fallback snippet", context.context_block)
        self.assertEqual(1, len(context.citations))
        self.assertEqual("doc-1", context.citations[0].document_id)

    def test_build_chat_context_caps_total_context_size(self) -> None:
        oversized_hits = [
            KnowledgeCitation(
                document_id=f"doc-{idx}",
                chunk_id=f"chunk-{idx}",
                filename=f"doc-{idx}.md",
                snippet="x" * 1200,
                score=0.9 - (idx * 0.01),
            )
            for idx in range(6)
        ]

        with patch(
            "backend.services.knowledge_service.search_knowledge",
            return_value=knowledge_service.KnowledgeSearchResponse(
                query="q",
                hits=oversized_hits,
            ),
        ):
            context = knowledge_service.build_chat_knowledge_context(
                query="q",
                document_ids=[],
                top_k=6,
                settings=self.settings,
                auth_context=_auth_context(),
            )

        self.assertLessEqual(len(context.context_block), 5200)
        self.assertLess(len(context.citations), len(oversized_hits))

    def test_start_knowledge_ingestion_marks_failure_when_normalization_fails(
        self,
    ) -> None:
        self._create_document("doc-2")

        with patch(
            "backend.services.knowledge_service.normalize_document",
            side_effect=ValueError("bad document"),
        ):
            with self.assertRaises(ValueError):
                knowledge_service.start_knowledge_ingestion(
                    request=KnowledgeIngestionRequest(document_id="doc-2"),
                    settings=self.settings,
                    auth_context=_auth_context(),
                )

        with sqlite3.connect(self.settings.log_db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT status, error_code, error_detail FROM knowledge_ingestions"
            ).fetchall()

        self.assertEqual(1, len(rows))
        self.assertEqual("failed", rows[0]["status"])
        self.assertEqual("KNOWLEDGE_INGESTION_FAILED", rows[0]["error_code"])
        self.assertIn("bad document", rows[0]["error_detail"])
