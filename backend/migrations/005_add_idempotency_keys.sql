-- Phase 13 Wave B: idempotency key storage for upload analyze + chat session append.
CREATE TABLE IF NOT EXISTS idempotency_keys (
    key TEXT NOT NULL,
    route TEXT NOT NULL,
    scope TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    response_status INTEGER,
    response_content_type TEXT,
    response_body TEXT,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    PRIMARY KEY (key, route, scope)
);

CREATE INDEX IF NOT EXISTS idx_idempotency_keys_expires_at
    ON idempotency_keys (expires_at);
