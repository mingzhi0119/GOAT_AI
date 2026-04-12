PRAGMA foreign_keys=OFF;

CREATE TABLE IF NOT EXISTS workbench_tasks_v2 (
    id TEXT PRIMARY KEY,
    task_kind TEXT NOT NULL CHECK (task_kind IN ('plan', 'browse', 'deep_research', 'canvas')),
    status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled')),
    prompt TEXT NOT NULL,
    session_id TEXT,
    project_id TEXT,
    knowledge_document_ids TEXT NOT NULL DEFAULT '[]',
    connector_ids TEXT NOT NULL DEFAULT '[]',
    source_ids TEXT NOT NULL DEFAULT '[]',
    error_detail TEXT,
    result_text TEXT,
    result_citations_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    auth_scopes_json TEXT NOT NULL DEFAULT '[]',
    credential_id TEXT NOT NULL DEFAULT '',
    auth_mode TEXT NOT NULL DEFAULT '',
    owner_id TEXT NOT NULL DEFAULT '',
    tenant_id TEXT NOT NULL DEFAULT 'tenant:default',
    principal_id TEXT NOT NULL DEFAULT ''
);

INSERT INTO workbench_tasks_v2 (
    id,
    task_kind,
    status,
    prompt,
    session_id,
    project_id,
    knowledge_document_ids,
    connector_ids,
    source_ids,
    error_detail,
    result_text,
    result_citations_json,
    created_at,
    updated_at,
    auth_scopes_json,
    credential_id,
    auth_mode,
    owner_id,
    tenant_id,
    principal_id
)
SELECT
    id,
    task_kind,
    status,
    prompt,
    session_id,
    project_id,
    knowledge_document_ids,
    connector_ids,
    source_ids,
    error_detail,
    result_text,
    result_citations_json,
    created_at,
    updated_at,
    auth_scopes_json,
    credential_id,
    auth_mode,
    owner_id,
    tenant_id,
    principal_id
FROM workbench_tasks;

DROP TABLE workbench_tasks;

ALTER TABLE workbench_tasks_v2 RENAME TO workbench_tasks;

CREATE INDEX IF NOT EXISTS idx_workbench_tasks_tenant_created
ON workbench_tasks (tenant_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_workbench_tasks_owner_created
ON workbench_tasks (owner_id, created_at DESC);

PRAGMA foreign_keys=ON;
