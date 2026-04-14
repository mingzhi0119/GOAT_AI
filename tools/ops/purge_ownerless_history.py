"""Purge legacy ownerless session history and linked audit rows."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from backend.platform.config import get_settings
from backend.services.privacy_cleanup import purge_ownerless_history


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Delete legacy ownerless sessions plus linked session_messages, "
            "chat_artifacts, and conversations rows."
        )
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Apply the deletion. Without this flag the command runs as a dry run.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    summary = purge_ownerless_history(
        settings=get_settings(),
        dry_run=not args.execute,
    )
    print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
