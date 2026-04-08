-- Baseline chat log and session tables (legacy-compatible shape before additive columns).
CREATE TABLE IF NOT EXISTS conversations (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at         TEXT    NOT NULL,
    ip                 TEXT    NOT NULL,
    model              TEXT    NOT NULL,
    turn_count         INTEGER NOT NULL,
    user_message       TEXT    NOT NULL,
    assistant_response TEXT    NOT NULL,
    response_ms        INTEGER
);

CREATE TABLE IF NOT EXISTS sessions (
    id         TEXT PRIMARY KEY,
    title      TEXT NOT NULL DEFAULT '',
    model      TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    messages   TEXT NOT NULL DEFAULT '[]'
);
