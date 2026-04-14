CREATE TABLE IF NOT EXISTS auth_users (
    id               TEXT PRIMARY KEY,
    email            TEXT NOT NULL,
    password_hash    TEXT NOT NULL DEFAULT '',
    display_name     TEXT NOT NULL,
    primary_provider TEXT NOT NULL DEFAULT 'local',
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_auth_users_email
    ON auth_users(email);

CREATE TABLE IF NOT EXISTS auth_user_identities (
    id               TEXT PRIMARY KEY,
    user_id          TEXT NOT NULL,
    provider         TEXT NOT NULL,
    provider_subject TEXT NOT NULL,
    email            TEXT NOT NULL,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES auth_users(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_auth_user_identities_provider_subject
    ON auth_user_identities(provider, provider_subject);

CREATE INDEX IF NOT EXISTS idx_auth_user_identities_user_id
    ON auth_user_identities(user_id);
