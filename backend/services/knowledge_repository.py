from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from backend.domain.resource_ownership import (
    PersistedResourceOwnership,
    ownership_from_fields,
)


@dataclass(frozen=True)
class KnowledgeDocumentRecord:
    id: str
    source_type: str
    original_filename: str
    mime_type: str
    sha256: str
    storage_path: str
    byte_size: int
    status: str
    created_at: str
    updated_at: str
    deleted_at: str | None
    storage_key: str = ""
    owner_id: str = ""
    tenant_id: str = "tenant:default"
    principal_id: str = ""

    @property
    def ownership(self) -> PersistedResourceOwnership:
        return ownership_from_fields(
            owner_id=self.owner_id,
            tenant_id=self.tenant_id,
            principal_id=self.principal_id,
        )


@dataclass(frozen=True)
class KnowledgeIngestionRecord:
    id: str
    document_id: str
    status: str
    parser_profile: str
    chunking_profile: str
    embedding_profile: str
    vector_backend: str
    started_at: str | None
    completed_at: str | None
    error_code: str | None
    error_detail: str | None
    chunk_count: int
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class KnowledgeChunkRow:
    id: str
    ingestion_id: str
    document_id: str
    chunk_index: int
    text_content: str
    text_hash: str
    token_count: int
    char_start: int
    char_end: int
    vector_ref: str
    created_at: str


class KnowledgeRepository(Protocol):
    def create_document(self, record: KnowledgeDocumentRecord) -> None: ...

    def get_document(self, document_id: str) -> KnowledgeDocumentRecord | None: ...

    def list_documents(
        self, document_ids: list[str]
    ) -> list[KnowledgeDocumentRecord]: ...

    def list_documents_for_tenant(
        self, tenant_id: str
    ) -> list[KnowledgeDocumentRecord]: ...

    def create_ingestion(self, record: KnowledgeIngestionRecord) -> None: ...

    def update_ingestion_status(
        self,
        *,
        ingestion_id: str,
        status: str,
        updated_at: str,
        chunk_count: int = 0,
        completed_at: str | None = None,
        error_code: str | None = None,
        error_detail: str | None = None,
    ) -> None: ...

    def get_ingestion(self, ingestion_id: str) -> KnowledgeIngestionRecord | None: ...

    def replace_chunks(
        self, *, ingestion_id: str, document_id: str, chunks: list[KnowledgeChunkRow]
    ) -> None: ...

    def get_chunks_for_documents(
        self, document_ids: list[str] | None = None
    ) -> list[KnowledgeChunkRow]: ...


class SQLiteKnowledgeRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def create_document(self, record: KnowledgeDocumentRecord) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO knowledge_documents
                    (id, source_type, original_filename, mime_type, sha256, storage_path, storage_key, byte_size, status, created_at, updated_at, deleted_at, owner_id, tenant_id, principal_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.source_type,
                    record.original_filename,
                    record.mime_type,
                    record.sha256,
                    record.storage_path,
                    record.storage_key,
                    record.byte_size,
                    record.status,
                    record.created_at,
                    record.updated_at,
                    record.deleted_at,
                    record.owner_id,
                    record.tenant_id,
                    record.principal_id,
                ),
            )

    def get_document(self, document_id: str) -> KnowledgeDocumentRecord | None:
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT id, source_type, original_filename, mime_type, sha256, storage_path, storage_key, byte_size, status, created_at, updated_at, deleted_at, owner_id, tenant_id, principal_id
                FROM knowledge_documents
                WHERE id = ? AND deleted_at IS NULL
                """,
                (document_id,),
            ).fetchone()
        if row is None:
            return None
        return KnowledgeDocumentRecord(**dict(row))

    def list_documents(self, document_ids: list[str]) -> list[KnowledgeDocumentRecord]:
        if not document_ids:
            return []
        placeholders = ", ".join("?" for _ in document_ids)
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"""
                SELECT id, source_type, original_filename, mime_type, sha256, storage_path, storage_key, byte_size, status, created_at, updated_at, deleted_at, owner_id, tenant_id, principal_id
                FROM knowledge_documents
                WHERE deleted_at IS NULL AND id IN ({placeholders})
                ORDER BY created_at ASC
                """,
                tuple(document_ids),
            ).fetchall()
        return [KnowledgeDocumentRecord(**dict(row)) for row in rows]

    def list_documents_for_tenant(
        self, tenant_id: str
    ) -> list[KnowledgeDocumentRecord]:
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT id, source_type, original_filename, mime_type, sha256, storage_path, storage_key, byte_size, status, created_at, updated_at, deleted_at, owner_id, tenant_id, principal_id
                FROM knowledge_documents
                WHERE deleted_at IS NULL AND tenant_id = ?
                ORDER BY created_at ASC
                """,
                (tenant_id,),
            ).fetchall()
        return [KnowledgeDocumentRecord(**dict(row)) for row in rows]

    def create_ingestion(self, record: KnowledgeIngestionRecord) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO knowledge_ingestions
                    (id, document_id, status, parser_profile, chunking_profile, embedding_profile, vector_backend, started_at, completed_at, error_code, error_detail, chunk_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.document_id,
                    record.status,
                    record.parser_profile,
                    record.chunking_profile,
                    record.embedding_profile,
                    record.vector_backend,
                    record.started_at,
                    record.completed_at,
                    record.error_code,
                    record.error_detail,
                    record.chunk_count,
                    record.created_at,
                    record.updated_at,
                ),
            )

    def update_ingestion_status(
        self,
        *,
        ingestion_id: str,
        status: str,
        updated_at: str,
        chunk_count: int = 0,
        completed_at: str | None = None,
        error_code: str | None = None,
        error_detail: str | None = None,
    ) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                UPDATE knowledge_ingestions
                SET status = ?, updated_at = ?, chunk_count = ?, completed_at = ?, error_code = ?, error_detail = ?
                WHERE id = ?
                """,
                (
                    status,
                    updated_at,
                    chunk_count,
                    completed_at,
                    error_code,
                    error_detail,
                    ingestion_id,
                ),
            )

    def get_ingestion(self, ingestion_id: str) -> KnowledgeIngestionRecord | None:
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT id, document_id, status, parser_profile, chunking_profile, embedding_profile, vector_backend,
                       started_at, completed_at, error_code, error_detail, chunk_count, created_at, updated_at
                FROM knowledge_ingestions
                WHERE id = ?
                """,
                (ingestion_id,),
            ).fetchone()
        if row is None:
            return None
        return KnowledgeIngestionRecord(**dict(row))

    def replace_chunks(
        self, *, ingestion_id: str, document_id: str, chunks: list[KnowledgeChunkRow]
    ) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "DELETE FROM knowledge_chunks WHERE ingestion_id = ?", (ingestion_id,)
            )
            conn.executemany(
                """
                INSERT INTO knowledge_chunks
                    (id, ingestion_id, document_id, chunk_index, text_content, text_hash, token_count, char_start, char_end, vector_ref, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        chunk.id,
                        chunk.ingestion_id,
                        chunk.document_id,
                        chunk.chunk_index,
                        chunk.text_content,
                        chunk.text_hash,
                        chunk.token_count,
                        chunk.char_start,
                        chunk.char_end,
                        chunk.vector_ref,
                        chunk.created_at,
                    )
                    for chunk in chunks
                ],
            )

    def get_chunks_for_documents(
        self, document_ids: list[str] | None = None
    ) -> list[KnowledgeChunkRow]:
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            if document_ids:
                placeholders = ", ".join("?" for _ in document_ids)
                rows = conn.execute(
                    f"""
                    SELECT id, ingestion_id, document_id, chunk_index, text_content, text_hash, token_count, char_start, char_end, vector_ref, created_at
                    FROM knowledge_chunks
                    WHERE document_id IN ({placeholders})
                    ORDER BY document_id, chunk_index
                    """,
                    tuple(document_ids),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, ingestion_id, document_id, chunk_index, text_content, text_hash, token_count, char_start, char_end, vector_ref, created_at
                    FROM knowledge_chunks
                    ORDER BY document_id, chunk_index
                    """
                ).fetchall()
        return [KnowledgeChunkRow(**dict(row)) for row in rows]
