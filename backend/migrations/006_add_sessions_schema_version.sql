-- Phase 13.4: session audit field for storage payload compatibility.
ALTER TABLE sessions ADD COLUMN schema_version INTEGER NOT NULL DEFAULT 1;
