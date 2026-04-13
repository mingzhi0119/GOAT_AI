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
    KnowledgeIngestionRecord,
    SQLiteKnowledgeRepository,
)
from goat_ai.config.settings import Settings


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
        object_store_root=root / "object-store",
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


class _KnowledgeAnswerFakeLLM:
    def __init__(self) -> None:
        self.last_model = ""
        self.last_prompt = ""

    def list_model_names(self) -> list[str]:
        return ["knowledge-answer-model"]

    def generate_completion(self, model: str, prompt: str, **_: object) -> str:
        self.last_model = model
        self.last_prompt = prompt
        if "Retrieved knowledge context:" in prompt:
            return "Synthesized answer grounded in the retrieved strategy note."
        return (
            "I could not find evidence in the indexed knowledge base for that question."
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

    def test_get_knowledge_upload_accepts_injected_repository(self) -> None:
        now = "2026-04-11T00:00:00+00:00"
        root = self.root

        class FakeKnowledgeRepository:
            def __init__(self) -> None:
                self.document = KnowledgeDocumentRecord(
                    id="doc-injected",
                    source_type="upload",
                    original_filename="doc-injected.md",
                    mime_type="text/markdown",
                    sha256="abc",
                    storage_path=str(root / "doc-injected.md"),
                    byte_size=64,
                    status="uploaded",
                    created_at=now,
                    updated_at=now,
                    deleted_at=None,
                    owner_id="owner-1",
                    tenant_id="tenant-1",
                    principal_id="principal-1",
                )

            def get_document(self, document_id: str) -> KnowledgeDocumentRecord | None:
                return self.document if document_id == self.document.id else None

            def get_chunks_for_documents(
                self, document_ids: list[str] | None = None
            ) -> list[KnowledgeChunkRow]:
                if document_ids == [self.document.id]:
                    return [
                        KnowledgeChunkRow(
                            id="chunk-1",
                            ingestion_id="ing-1",
                            document_id=self.document.id,
                            chunk_index=0,
                            text_content="Indexed content.",
                            text_hash="hash",
                            token_count=2,
                            char_start=0,
                            char_end=15,
                            vector_ref="doc-injected:0",
                            created_at=now,
                        )
                    ]
                return []

            def list_documents(
                self, document_ids: list[str]
            ) -> list[KnowledgeDocumentRecord]:
                return [
                    self.document
                    for document_id in document_ids
                    if document_id == self.document.id
                ]

            def list_documents_for_tenant(
                self, tenant_id: str
            ) -> list[KnowledgeDocumentRecord]:
                return [self.document] if tenant_id == "tenant-1" else []

            def create_document(self, record: KnowledgeDocumentRecord) -> None:
                self.document = record

            def create_ingestion(self, record: KnowledgeIngestionRecord) -> None:
                return None

            def update_ingestion_status(self, **_: object) -> None:
                return None

            def get_ingestion(
                self, ingestion_id: str
            ) -> KnowledgeIngestionRecord | None:
                return None

            def replace_chunks(
                self,
                *,
                ingestion_id: str,
                document_id: str,
                chunks: list[KnowledgeChunkRow],
            ) -> None:
                return None

        repository = FakeKnowledgeRepository()

        response = knowledge_service.get_knowledge_upload(
            document_id="doc-injected",
            settings=self.settings,
            auth_context=_auth_context(),
            repository=repository,
        )

        self.assertEqual("indexed", response.status)
        self.assertEqual("doc-injected", response.document_id)

    def test_create_knowledge_upload_persists_original_blob_in_object_store_root(
        self,
    ) -> None:
        response = knowledge_service.create_knowledge_upload_from_bytes(
            content=b"Porter Five Forces",
            filename="strategy.txt",
            content_type="text/plain",
            settings=self.settings,
            auth_context=_auth_context(),
            repository=self.repository,
        )

        stored = self.repository.get_document(response.document_id)
        self.assertIsNotNone(stored)
        assert stored is not None
        self.assertTrue(stored.storage_key.startswith("knowledge/"))
        self.assertTrue(Path(stored.storage_path).is_file())
        self.assertTrue(
            str(Path(stored.storage_path)).startswith(
                str(self.settings.object_store_root)
            )
        )

    def test_resolve_knowledge_documents_preserves_order_with_injected_repository(
        self,
    ) -> None:
        now = "2026-04-11T00:00:00+00:00"
        documents = {
            "doc-a": KnowledgeDocumentRecord(
                id="doc-a",
                source_type="upload",
                original_filename="a.md",
                mime_type="text/markdown",
                sha256="a",
                storage_path=str(self.root / "a.md"),
                byte_size=10,
                status="uploaded",
                created_at=now,
                updated_at=now,
                deleted_at=None,
                owner_id="owner-1",
                tenant_id="tenant-1",
                principal_id="principal-1",
            ),
            "doc-b": KnowledgeDocumentRecord(
                id="doc-b",
                source_type="upload",
                original_filename="b.md",
                mime_type="text/markdown",
                sha256="b",
                storage_path=str(self.root / "b.md"),
                byte_size=10,
                status="uploaded",
                created_at=now,
                updated_at=now,
                deleted_at=None,
                owner_id="owner-1",
                tenant_id="tenant-1",
                principal_id="principal-1",
            ),
        }

        class FakeKnowledgeRepository:
            def list_documents(
                self, document_ids: list[str]
            ) -> list[KnowledgeDocumentRecord]:
                # Intentionally return out of order to prove service reorders.
                return [documents["doc-b"], documents["doc-a"]]

        resolved = knowledge_service.resolve_knowledge_documents(
            document_ids=["doc-a", "doc-b", "doc-a"],
            settings=self.settings,
            auth_context=_auth_context(),
            repository=FakeKnowledgeRepository(),
        )

        self.assertEqual(["doc-a", "doc-b"], [document.id for document in resolved])

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

    def test_answer_with_knowledge_returns_synthesized_answer_and_citations(
        self,
    ) -> None:
        fake_llm = _KnowledgeAnswerFakeLLM()
        citations = [
            KnowledgeCitation(
                document_id="doc-1",
                chunk_id="chunk-1",
                filename="strategy.md",
                snippet="Competitive pressure stays high when buyer power increases.",
                score=0.91,
            )
        ]

        with patch(
            "backend.services.knowledge_service.build_chat_knowledge_context",
            return_value=knowledge_service.KnowledgeChatContext(
                context_block="[Source 1] filename=strategy.md score=0.910\nCompetitive pressure stays high when buyer power increases.",
                citations=citations,
            ),
        ):
            response = knowledge_service.answer_with_knowledge(
                request=knowledge_service.KnowledgeAnswerRequest(
                    query="Summarize the strategy note",
                    document_ids=["doc-1"],
                    top_k=3,
                ),
                llm=fake_llm,
                settings=self.settings,
                auth_context=_auth_context(),
            )

        self.assertEqual(
            "Synthesized answer grounded in the retrieved strategy note.",
            response.answer,
        )
        self.assertEqual(citations, response.citations)
        self.assertEqual("knowledge-answer-model", fake_llm.last_model)
        self.assertIn("synthesize rather than dumping snippets", fake_llm.last_prompt)
        self.assertIn(
            "User question:\nSummarize the strategy note", fake_llm.last_prompt
        )

    def test_answer_with_knowledge_synthesizes_no_hit_response(self) -> None:
        fake_llm = _KnowledgeAnswerFakeLLM()

        with patch(
            "backend.services.knowledge_service.build_chat_knowledge_context",
            return_value=knowledge_service.KnowledgeChatContext(
                context_block="",
                citations=[],
            ),
        ):
            response = knowledge_service.answer_with_knowledge(
                request=knowledge_service.KnowledgeAnswerRequest(
                    query="What does the missing note say?",
                    document_ids=[],
                    top_k=3,
                ),
                llm=fake_llm,
                settings=self.settings,
                auth_context=_auth_context(),
            )

        self.assertEqual([], response.citations)
        self.assertEqual(
            "I could not find evidence in the indexed knowledge base for that question.",
            response.answer,
        )
        self.assertIn("No relevant retrieved context was found", fake_llm.last_prompt)

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
