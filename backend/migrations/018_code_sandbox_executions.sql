CREATE TABLE IF NOT EXISTS code_sandbox_executions (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    runtime_preset TEXT NOT NULL,
    network_policy TEXT NOT NULL,
    code TEXT,
    command TEXT,
    stdin_text TEXT,
    inline_files_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    exit_code INTEGER,
    stdout TEXT NOT NULL DEFAULT '',
    stderr TEXT NOT NULL DEFAULT '',
    timed_out INTEGER NOT NULL DEFAULT 0,
    error_detail TEXT,
    output_files_json TEXT,
    provider_name TEXT NOT NULL DEFAULT '',
    owner_id TEXT NOT NULL DEFAULT '',
    tenant_id TEXT NOT NULL DEFAULT 'tenant:default',
    principal_id TEXT NOT NULL DEFAULT '',
    auth_scopes_json TEXT NOT NULL DEFAULT '[]',
    credential_id TEXT NOT NULL DEFAULT '',
    auth_mode TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS code_sandbox_execution_events (
    execution_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT,
    message TEXT,
    metadata_json TEXT,
    PRIMARY KEY (execution_id, seq),
    FOREIGN KEY (execution_id) REFERENCES code_sandbox_executions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_code_sandbox_executions_updated_at
ON code_sandbox_executions(updated_at);

CREATE INDEX IF NOT EXISTS idx_code_sandbox_execution_events_created_at
ON code_sandbox_execution_events(execution_id, created_at);
