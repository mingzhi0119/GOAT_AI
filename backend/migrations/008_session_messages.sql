-- Phase 15.4: normalized per-message rows (dual-read with legacy sessions.messages JSON).
-- Rows mirror the visible ``messages`` array in the versioned session payload (role, content, optional image ids).

CREATE TABLE IF NOT EXISTS session_messages (
    session_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    image_attachment_ids TEXT,
    created_at TEXT NOT NULL,
    PRIMARY KEY (session_id, seq)
);

CREATE INDEX IF NOT EXISTS idx_session_messages_session ON session_messages(session_id);
