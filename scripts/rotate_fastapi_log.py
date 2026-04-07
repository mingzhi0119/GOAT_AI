"""Rotate deploy.sh fastapi.log when it exceeds a size threshold (user-space, no logrotate)."""
from __future__ import annotations

import argparse
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path


def _default_project_root() -> Path:
    """Repo root: GOAT_AI_ROOT env, else parent of scripts/."""
    env = os.environ.get("GOAT_AI_ROOT", "").strip()
    if env:
        p = Path(env).resolve()
        if p.is_dir():
            return p
    return Path(__file__).resolve().parent.parent


def resolve_log_path(project_root: Path) -> Path:
    """Path to fastapi.log (GOAT_FASTAPI_LOG overrides)."""
    override = os.environ.get("GOAT_FASTAPI_LOG", "").strip()
    if override:
        return Path(override).resolve()
    return (project_root / "logs" / "fastapi.log").resolve()


def resolve_archive_dir(project_root: Path) -> Path:
    """Directory for rotated logs (GOAT_LOG_ARCHIVE_DIR overrides)."""
    override = os.environ.get("GOAT_LOG_ARCHIVE_DIR", "").strip()
    if override:
        return Path(override).resolve()
    return (project_root / "logs" / "archive").resolve()


def _parse_max_bytes() -> int:
    mb = float(os.environ.get("GOAT_LOG_MAX_MB", "50"))
    return int(mb * 1024 * 1024)


def _parse_keep_archives() -> int:
    return max(1, int(os.environ.get("GOAT_LOG_KEEP_ARCHIVES", "14")))


def prune_old_archives(archive_dir: Path, pattern_prefix: str, keep: int) -> list[Path]:
    """Remove oldest matching files beyond keep count; returns deleted paths."""
    if not archive_dir.is_dir():
        return []
    candidates = sorted(
        (p for p in archive_dir.iterdir() if p.is_file() and p.name.startswith(pattern_prefix)),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    deleted: list[Path] = []
    for p in candidates[keep:]:
        p.unlink(missing_ok=True)
        deleted.append(p)
    return deleted


def rotate_fastapi_log(
    log_path: Path,
    *,
    max_bytes: int,
    archive_dir: Path,
    keep_archives: int,
    dry_run: bool = False,
) -> bool:
    """Copy oversized log to archive and truncate the original. Returns True if rotated."""
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")
    if not log_path.is_file():
        return False
    size = log_path.stat().st_size
    if size <= max_bytes:
        return False
    if dry_run:
        return True
    archive_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive_path = archive_dir / f"fastapi_{ts}.log"
    shutil.copy2(log_path, archive_path)
    with log_path.open("r+b") as f:
        f.truncate(0)
    prune_old_archives(archive_dir, "fastapi_", keep_archives)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Rotate fastapi.log when it exceeds GOAT_LOG_MAX_MB.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print whether rotation would occur without writing",
    )
    parser.add_argument("--max-mb", type=float, default=None, help="Override GOAT_LOG_MAX_MB")
    parser.add_argument("--keep", type=int, default=None, help="Override GOAT_LOG_KEEP_ARCHIVES")
    parser.add_argument("--project-root", type=Path, default=None, help="Override GOAT_AI_ROOT")
    args = parser.parse_args()

    project_root = (args.project_root.resolve() if args.project_root else _default_project_root())
    log_path = resolve_log_path(project_root)
    archive_dir = resolve_archive_dir(project_root)
    max_bytes = int(args.max_mb * 1024 * 1024) if args.max_mb is not None else _parse_max_bytes()
    keep = args.keep if args.keep is not None else _parse_keep_archives()

    rotated = rotate_fastapi_log(
        log_path,
        max_bytes=max_bytes,
        archive_dir=archive_dir,
        keep_archives=keep,
        dry_run=bool(args.dry_run),
    )
    if args.dry_run:
        status = "would rotate" if rotated else "skip (under threshold or missing)"
        print(f"{status}: {log_path}")
        return
    if rotated:
        print(f"Rotated: {log_path} -> {archive_dir}/fastapi_*.log")
    else:
        print(f"No rotation: {log_path} (missing or under {max_bytes} bytes)")


if __name__ == "__main__":
    main()
