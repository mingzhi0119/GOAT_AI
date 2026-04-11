ALTER TABLE code_sandbox_executions
ADD COLUMN execution_mode TEXT NOT NULL DEFAULT 'sync';

ALTER TABLE code_sandbox_executions
ADD COLUMN queued_at TEXT NOT NULL DEFAULT '';

ALTER TABLE code_sandbox_executions
ADD COLUMN timeout_sec INTEGER NOT NULL DEFAULT 8;

ALTER TABLE code_sandbox_executions
ADD COLUMN last_log_seq INTEGER NOT NULL DEFAULT 0;

UPDATE code_sandbox_executions
SET queued_at = CASE
    WHEN queued_at = '' OR queued_at IS NULL THEN created_at
    ELSE queued_at
END;

CREATE TABLE IF NOT EXISTS code_sandbox_execution_logs (
    execution_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    stream_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    chunk_text TEXT NOT NULL,
    PRIMARY KEY (execution_id, seq),
    FOREIGN KEY (execution_id) REFERENCES code_sandbox_executions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_code_sandbox_execution_logs_created_at
ON code_sandbox_execution_logs(execution_id, created_at);
