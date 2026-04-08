-- Tracks applied SQL migrations (Phase 13 §13.0). Applied in lexicographic filename order.
CREATE TABLE IF NOT EXISTS schema_migrations (
    id TEXT PRIMARY KEY NOT NULL,
    applied_at TEXT NOT NULL,
    checksum TEXT NOT NULL
);
