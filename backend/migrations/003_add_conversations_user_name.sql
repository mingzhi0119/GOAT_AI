-- Add user_name to conversation audit rows (idempotent at runner level if column exists).
ALTER TABLE conversations ADD COLUMN user_name TEXT NOT NULL DEFAULT '';
