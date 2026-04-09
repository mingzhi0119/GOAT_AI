ALTER TABLE sessions ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'tenant:default';
ALTER TABLE sessions ADD COLUMN principal_id TEXT NOT NULL DEFAULT '';

ALTER TABLE chat_artifacts ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'tenant:default';
ALTER TABLE chat_artifacts ADD COLUMN principal_id TEXT NOT NULL DEFAULT '';

CREATE INDEX IF NOT EXISTS idx_sessions_tenant_id
    ON sessions(tenant_id);

CREATE INDEX IF NOT EXISTS idx_chat_artifacts_tenant_id
    ON chat_artifacts(tenant_id);
