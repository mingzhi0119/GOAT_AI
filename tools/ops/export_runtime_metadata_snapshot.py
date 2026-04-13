"""Export a deterministic JSON snapshot of GOAT SQLite runtime metadata."""

from __future__ import annotations

import argparse
from pathlib import Path

from backend.services.runtime_metadata_snapshot import (
    write_sqlite_runtime_metadata_snapshot,
)
from goat_ai.config.settings import load_settings


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export the governed SQLite runtime metadata surface as JSON."
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Override the SQLite runtime metadata DB path (default from settings).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Destination JSON snapshot path.",
    )
    args = parser.parse_args()

    settings = load_settings()
    db_path = args.db.resolve() if args.db else settings.log_db_path
    out_path = args.out.resolve()
    written = write_sqlite_runtime_metadata_snapshot(
        db_path=db_path,
        out_path=out_path,
    )
    print(f"Runtime metadata snapshot written: {written}")


if __name__ == "__main__":
    main()
