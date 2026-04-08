CREATE TABLE IF NOT EXISTS chat_artifacts (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL DEFAULT '',
    owner_id TEXT NOT NULL DEFAULT '',
    filename TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    byte_size INTEGER NOT NULL,
    storage_path TEXT NOT NULL,
    source_message_index INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_chat_artifacts_session_id
    ON chat_artifacts(session_id);

CREATE INDEX IF NOT EXISTS idx_chat_artifacts_owner_id
    ON chat_artifacts(owner_id);

ALTER TABLE session_messages ADD COLUMN artifacts_json TEXT;
