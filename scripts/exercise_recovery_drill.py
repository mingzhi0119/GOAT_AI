"""Exercise SQLite backup, restore, and rollback paths against one database."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from scripts.backup_chat_db import backup_chat_db


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="exercise-recovery-drill",
        description=(
            "Exercise backup, restore, and rollback paths for one GOAT AI SQLite DB."
        ),
    )
    parser.add_argument("--src", type=Path, required=True)
    parser.add_argument("--backup-dir", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, default=None)
    parser.add_argument("--max-files", type=int, default=14)
    parser.add_argument(
        "--required-table",
        action="append",
        default=None,
        help="Repeat to require specific tables during the drill.",
    )
    return parser


@dataclass(frozen=True)
class RecoveryDrillResult:
    backup_path: str
    restore_target_path: str
    rollback_copy_path: str
    backup_sha256: str
    restored_sha256: str
    rolled_back_sha256: str
    verified_tables: list[str]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sqlite_integrity_check(db_path: Path) -> str:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("PRAGMA integrity_check").fetchone()
    if row is None or not isinstance(row[0], str):
        raise ValueError(f"SQLite integrity_check returned no result for {db_path}")
    return row[0]


def _assert_sqlite_ok(db_path: Path) -> None:
    result = _sqlite_integrity_check(db_path)
    if result != "ok":
        raise ValueError(f"SQLite integrity check failed for {db_path}: {result}")


def _assert_required_tables(db_path: Path, required_tables: list[str]) -> None:
    if not required_tables:
        return
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    present = {str(row[0]) for row in rows if row and row[0]}
    missing = [table for table in required_tables if table not in present]
    if missing:
        raise ValueError(
            f"Recovery drill missing required tables in {db_path}: {', '.join(missing)}"
        )


def exercise_recovery_drill(
    *,
    src: Path,
    backup_dir: Path,
    max_files: int,
    required_tables: list[str] | None = None,
    work_dir: Path | None = None,
) -> RecoveryDrillResult:
    normalized_required_tables = [
        table.strip() for table in (required_tables or []) if table.strip()
    ]
    backup_path = backup_chat_db(
        src.resolve(), backup_dir.resolve(), max_files=max_files
    )
    _assert_sqlite_ok(backup_path)
    _assert_required_tables(backup_path, normalized_required_tables)

    if work_dir is None:
        with tempfile.TemporaryDirectory(prefix="goat-recovery-drill-") as tmp:
            return exercise_recovery_drill(
                src=src,
                backup_dir=backup_dir,
                max_files=max_files,
                required_tables=normalized_required_tables,
                work_dir=Path(tmp),
            )

    resolved_work_dir = work_dir.resolve()
    resolved_work_dir.mkdir(parents=True, exist_ok=True)
    restore_target = resolved_work_dir / "chat_logs.restore_target.db"
    rollback_copy = resolved_work_dir / "chat_logs.rollback_copy.db"

    shutil.copy2(src.resolve(), restore_target)
    shutil.copy2(restore_target, rollback_copy)
    original_hash = _sha256_file(restore_target)

    shutil.copy2(backup_path, restore_target)
    _assert_sqlite_ok(restore_target)
    _assert_required_tables(restore_target, normalized_required_tables)
    restored_hash = _sha256_file(restore_target)

    shutil.copy2(rollback_copy, restore_target)
    _assert_sqlite_ok(restore_target)
    _assert_required_tables(restore_target, normalized_required_tables)
    rolled_back_hash = _sha256_file(restore_target)

    if rolled_back_hash != original_hash:
        raise ValueError("Rollback drill did not restore the original database bytes.")

    return RecoveryDrillResult(
        backup_path=str(backup_path),
        restore_target_path=str(restore_target),
        rollback_copy_path=str(rollback_copy),
        backup_sha256=_sha256_file(backup_path),
        restored_sha256=restored_hash,
        rolled_back_sha256=rolled_back_hash,
        verified_tables=normalized_required_tables,
    )


def main() -> int:
    args = _build_parser().parse_args()
    result = exercise_recovery_drill(
        src=args.src,
        backup_dir=args.backup_dir,
        max_files=args.max_files,
        required_tables=list(args.required_table or []),
        work_dir=args.work_dir,
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
