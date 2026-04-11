ALTER TABLE workbench_tasks
ADD COLUMN source_ids TEXT NOT NULL DEFAULT '[]';

ALTER TABLE workbench_tasks
ADD COLUMN auth_scopes_json TEXT NOT NULL DEFAULT '[]';

ALTER TABLE workbench_tasks
ADD COLUMN credential_id TEXT NOT NULL DEFAULT '';

ALTER TABLE workbench_tasks
ADD COLUMN auth_mode TEXT NOT NULL DEFAULT '';

UPDATE workbench_tasks
SET source_ids = connector_ids
WHERE source_ids = '[]';
