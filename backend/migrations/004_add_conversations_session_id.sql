-- Link conversation audit rows to sidebar session id when present.
ALTER TABLE conversations ADD COLUMN session_id TEXT;
