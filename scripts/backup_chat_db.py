"""Online backup of GOAT SQLite chat DB (safe while the app holds the file open)."""
from __future__ import annotations

import argparse
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from goat_ai.config import load_settings


def _default_project_root() -> Path:
    env = os.environ.get("GOAT_AI_ROOT", "").strip()
    if env:
        p = Path(env).resolve()
        if p.is_dir():
            return p
    return Path(__file__).resolve().parent.parent


def resolve_backup_dir(project_root: Path) -> Path:
    """Destination directory (GOAT_BACKUP_DIR overrides)."""
    override = os.environ.get("GOAT_BACKUP_DIR", "").strip()
    if override:
        return Path(override).resolve()
    return (project_root / "backups").resolve()


def _parse_max_files() -> int:
    return max(1, int(os.environ.get("GOAT_BACKUP_MAX_FILES", "14")))


def prune_old_backups(backup_dir: Path, prefix: str, suffix: str, keep: int) -> list[Path]:
    """Remove oldest chat_logs_*.db beyond keep; returns deleted paths."""
    if not backup_dir.is_dir():
        return []
    candidates = sorted(
        (
            p
            for p in backup_dir.iterdir()
            if p.is_file() and p.name.startswith(prefix) and p.name.endswith(suffix)
        ),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    deleted: list[Path] = []
    for p in candidates[keep:]:
        p.unlink(missing_ok=True)
        deleted.append(p)
    return deleted


def backup_chat_db(
    src: Path,
    dest_dir: Path,
    *,
    max_files: int,
) -> Path:
    """Run sqlite3 online backup to a timestamped file under dest_dir."""
    if not src.is_file():
        raise FileNotFoundError(f"SQLite database not found: {src}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest = dest_dir / f"chat_logs_{ts}.db"
    src_conn = sqlite3.connect(src)
    try:
        dest_conn = sqlite3.connect(dest)
        try:
            with dest_conn:
                src_conn.backup(dest_conn)
        finally:
            dest_conn.close()
    finally:
        src_conn.close()
    prune_old_backups(dest_dir, "chat_logs_", ".db", max_files)
    return dest


def main() -> None:
    parser = argparse.ArgumentParser(description="Backup GOAT chat SQLite DB via sqlite3.backup().")
    parser.add_argument("--project-root", type=Path, default=None, help="Override GOAT_AI_ROOT")
    parser.add_argument("--src", type=Path, default=None, help="Override database path (default from GOAT_LOG_PATH / settings)")
    parser.add_argument("--dest-dir", type=Path, default=None, help="Override backup directory")
    parser.add_argument("--max-files", type=int, default=None, help="Override GOAT_BACKUP_MAX_FILES")
    args = parser.parse_args()

    project_root = (args.project_root.resolve() if args.project_root else _default_project_root())
    settings = load_settings()
    src = args.src.resolve() if args.src else settings.log_db_path
    dest_dir = args.dest_dir.resolve() if args.dest_dir else resolve_backup_dir(project_root)
    max_files = args.max_files if args.max_files is not None else _parse_max_files()

    out = backup_chat_db(src, dest_dir, max_files=max_files)
    print(f"Backup written: {out}")


if __name__ == "__main__":
    main()
