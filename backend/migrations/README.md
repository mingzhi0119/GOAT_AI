# SQL migrations

Numbered files `NNN_description.sql` run in lexicographic order at application startup (see `backend.services.db_migrations`). The `schema_migrations` table tracks applied ids and file checksums.

Do not edit a migration after it has shipped to production; add a new file instead.
