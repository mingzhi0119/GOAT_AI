-- Phase 14 RAG-1: knowledge document, ingestion, and chunk metadata.
CREATE TABLE IF NOT EXISTS knowledge_documents (
    id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    byte_size INTEGER NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_knowledge_documents_status
    ON knowledge_documents(status);

CREATE INDEX IF NOT EXISTS idx_knowledge_documents_created_at
    ON knowledge_documents(created_at);

CREATE TABLE IF NOT EXISTS knowledge_ingestions (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    status TEXT NOT NULL,
    parser_profile TEXT NOT NULL,
    chunking_profile TEXT NOT NULL,
    embedding_profile TEXT NOT NULL,
    vector_backend TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    error_code TEXT,
    error_detail TEXT,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (document_id) REFERENCES knowledge_documents(id)
);

CREATE INDEX IF NOT EXISTS idx_knowledge_ingestions_document_id
    ON knowledge_ingestions(document_id);

CREATE INDEX IF NOT EXISTS idx_knowledge_ingestions_status
    ON knowledge_ingestions(status);

CREATE INDEX IF NOT EXISTS idx_knowledge_ingestions_created_at
    ON knowledge_ingestions(created_at);

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id TEXT PRIMARY KEY,
    ingestion_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    text_content TEXT NOT NULL,
    text_hash TEXT NOT NULL,
    token_count INTEGER,
    char_start INTEGER,
    char_end INTEGER,
    page_number INTEGER,
    section_label TEXT,
    vector_ref TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (ingestion_id) REFERENCES knowledge_ingestions(id),
    FOREIGN KEY (document_id) REFERENCES knowledge_documents(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_chunks_ingestion_chunk
    ON knowledge_chunks(ingestion_id, chunk_index);

CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_document_id
    ON knowledge_chunks(document_id);

CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_vector_ref
    ON knowledge_chunks(vector_ref);
