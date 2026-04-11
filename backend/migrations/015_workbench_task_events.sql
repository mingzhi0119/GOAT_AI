CREATE TABLE IF NOT EXISTS workbench_task_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT,
    message TEXT,
    metadata_json TEXT,
    FOREIGN KEY(task_id) REFERENCES workbench_tasks(id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_workbench_task_events_task_seq
ON workbench_task_events (task_id, seq);

CREATE INDEX IF NOT EXISTS idx_workbench_task_events_task_created
ON workbench_task_events (task_id, created_at ASC, seq ASC);
