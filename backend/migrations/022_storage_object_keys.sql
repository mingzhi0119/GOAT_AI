ALTER TABLE knowledge_documents ADD COLUMN storage_key TEXT NOT NULL DEFAULT '';
ALTER TABLE chat_artifacts ADD COLUMN storage_key TEXT NOT NULL DEFAULT '';
ALTER TABLE media_uploads ADD COLUMN storage_key TEXT NOT NULL DEFAULT '';
