from __future__ import annotations

import unittest

from __tests__.helpers.postgres_runtime import postgres_runtime_container
from backend.services.postgres_runtime_support import (
    current_postgres_alembic_revision,
    ensure_postgres_runtime_metadata_tables_exist,
    postgres_connect,
    run_postgres_runtime_migrations,
)


class PostgresRuntimeMigrationsTests(unittest.TestCase):
    def test_upgrade_to_head_is_idempotent_and_creates_inventory(self) -> None:
        with postgres_runtime_container() as dsn:
            run_postgres_runtime_migrations(dsn)
            run_postgres_runtime_migrations(dsn)

            self.assertEqual("20260413_01", current_postgres_alembic_revision(dsn))
            with postgres_connect(dsn) as conn:
                ensure_postgres_runtime_metadata_tables_exist(conn)
                conversations_columns = {
                    str(row["column_name"])
                    for row in conn.execute(
                        """
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_name = 'conversations'
                        """
                    ).fetchall()
                }
                self.assertIn("session_id", conversations_columns)
                self.assertIn("user_name", conversations_columns)


if __name__ == "__main__":
    unittest.main()
