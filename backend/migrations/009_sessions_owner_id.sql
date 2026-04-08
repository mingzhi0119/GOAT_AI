-- Phase 15.5: optional session ownership for multi-principal deployments (see OPERATIONS.md).

ALTER TABLE sessions ADD COLUMN owner_id TEXT NOT NULL DEFAULT '';
