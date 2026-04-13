"""Run Alembic upgrades for the hosted Postgres runtime metadata schema."""

from __future__ import annotations

import argparse

from backend.services.postgres_runtime_support import run_postgres_runtime_migrations
from goat_ai.config.settings import load_settings


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upgrade the hosted Postgres runtime metadata schema to Alembic head."
    )
    parser.add_argument(
        "--dsn",
        type=str,
        default="",
        help="Override Postgres DSN (default from settings).",
    )
    args = parser.parse_args()

    settings = load_settings()
    dsn = args.dsn.strip() or settings.runtime_postgres_dsn
    if not dsn:
        raise SystemExit("Postgres DSN is required for Alembic upgrade.")

    run_postgres_runtime_migrations(dsn)
    print("Hosted Postgres runtime metadata schema upgraded to Alembic head.")


if __name__ == "__main__":
    main()
