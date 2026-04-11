CREATE TABLE IF NOT EXISTS workbench_workspace_outputs (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    output_kind TEXT NOT NULL CHECK (output_kind IN ('canvas_document')),
    title TEXT NOT NULL,
    content_format TEXT NOT NULL CHECK (content_format IN ('markdown')),
    content_text TEXT NOT NULL,
    metadata_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    owner_id TEXT NOT NULL DEFAULT '',
    tenant_id TEXT NOT NULL DEFAULT 'tenant:default',
    principal_id TEXT NOT NULL DEFAULT '',
    FOREIGN KEY(task_id) REFERENCES workbench_tasks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_workbench_workspace_outputs_task_created
ON workbench_workspace_outputs (task_id, created_at ASC, id ASC);

CREATE INDEX IF NOT EXISTS idx_workbench_workspace_outputs_tenant_created
ON workbench_workspace_outputs (tenant_id, created_at DESC);
