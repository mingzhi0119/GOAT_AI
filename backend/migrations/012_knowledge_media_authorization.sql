ALTER TABLE knowledge_documents ADD COLUMN owner_id TEXT NOT NULL DEFAULT '';
ALTER TABLE knowledge_documents ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'tenant:default';
ALTER TABLE knowledge_documents ADD COLUMN principal_id TEXT NOT NULL DEFAULT '';

CREATE INDEX IF NOT EXISTS idx_knowledge_documents_tenant_id
    ON knowledge_documents(tenant_id);

CREATE TABLE IF NOT EXISTS media_uploads (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL DEFAULT '',
    tenant_id TEXT NOT NULL DEFAULT 'tenant:default',
    principal_id TEXT NOT NULL DEFAULT '',
    filename TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    byte_size INTEGER NOT NULL,
    storage_path TEXT NOT NULL,
    width_px INTEGER,
    height_px INTEGER,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_media_uploads_tenant_id
    ON media_uploads(tenant_id);
