"""Compare a runtime-metadata snapshot against a live Postgres runtime store."""

from __future__ import annotations

import argparse
from pathlib import Path

from backend.services.runtime_metadata_snapshot import (
    compare_runtime_metadata_snapshot_to_postgres,
    read_runtime_metadata_snapshot,
)
from goat_ai.config.settings import load_settings


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check Postgres runtime metadata parity against an expected snapshot."
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        required=True,
        help="Path to the exported runtime metadata snapshot JSON file.",
    )
    parser.add_argument(
        "--dsn",
        type=str,
        default="",
        help="Override the Postgres DSN (default from settings).",
    )
    args = parser.parse_args()

    settings = load_settings()
    dsn = args.dsn.strip() or settings.runtime_postgres_dsn
    if not dsn:
        raise SystemExit(
            "A Postgres DSN is required via --dsn or GOAT_RUNTIME_POSTGRES_DSN."
        )
    snapshot = read_runtime_metadata_snapshot(args.snapshot.resolve())
    mismatches = compare_runtime_metadata_snapshot_to_postgres(
        snapshot=snapshot,
        dsn=dsn,
    )
    if mismatches:
        for mismatch in mismatches:
            print(mismatch)
        raise SystemExit(1)
    print("Runtime metadata parity check passed.")


if __name__ == "__main__":
    main()
