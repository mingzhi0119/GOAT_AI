CREATE TABLE IF NOT EXISTS workbench_tasks (
    id TEXT PRIMARY KEY,
    task_kind TEXT NOT NULL CHECK (task_kind IN ('plan', 'browse', 'deep_research', 'canvas')),
    status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'completed', 'failed')),
    prompt TEXT NOT NULL,
    session_id TEXT,
    project_id TEXT,
    knowledge_document_ids TEXT NOT NULL DEFAULT '[]',
    connector_ids TEXT NOT NULL DEFAULT '[]',
    error_detail TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    owner_id TEXT NOT NULL DEFAULT '',
    tenant_id TEXT NOT NULL DEFAULT 'tenant:default',
    principal_id TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_workbench_tasks_tenant_created
ON workbench_tasks (tenant_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_workbench_tasks_owner_created
ON workbench_tasks (owner_id, created_at DESC);
