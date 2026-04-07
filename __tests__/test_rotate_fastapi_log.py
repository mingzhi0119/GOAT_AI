"""Tests for scripts/rotate_fastapi_log.py."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.rotate_fastapi_log import (
    prune_old_archives,
    resolve_archive_dir,
    resolve_log_path,
    rotate_fastapi_log,
)


class RotateFastapiLogTests(unittest.TestCase):
    def test_resolve_log_path_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p = resolve_log_path(root)
            self.assertEqual(root / "logs" / "fastapi.log", p)

    def test_resolve_archive_dir_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = resolve_archive_dir(root)
            self.assertEqual(root / "logs" / "archive", d)

    def test_rotate_truncates_and_archives(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log_path = root / "logs" / "fastapi.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text("x" * 100, encoding="utf-8")
            archive_dir = root / "logs" / "archive"
            did = rotate_fastapi_log(
                log_path,
                max_bytes=50,
                archive_dir=archive_dir,
                keep_archives=10,
            )
            self.assertTrue(did)
            self.assertEqual(log_path.read_text(encoding="utf-8"), "")
            archived = list(archive_dir.glob("fastapi_*.log"))
            self.assertEqual(len(archived), 1)
            self.assertEqual(archived[0].read_text(encoding="utf-8"), "x" * 100)

    def test_no_op_when_small(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log_path = root / "logs" / "fastapi.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text("small", encoding="utf-8")
            archive_dir = root / "logs" / "archive"
            did = rotate_fastapi_log(
                log_path,
                max_bytes=10_000,
                archive_dir=archive_dir,
                keep_archives=10,
            )
            self.assertFalse(did)
            self.assertEqual(log_path.read_text(encoding="utf-8"), "small")
            self.assertFalse(archive_dir.exists())

    def test_missing_log_no_op(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "nope.log"
            did = rotate_fastapi_log(
                log_path,
                max_bytes=1,
                archive_dir=Path(tmp) / "arch",
                keep_archives=10,
            )
            self.assertFalse(did)

    def test_prune_old_archives(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ad = Path(tmp)
            for i in range(5):
                p = ad / f"fastapi_old{i}.log"
                p.write_text("a", encoding="utf-8")
                # stagger mtimes
                import os

                os.utime(p, (1000 + i, 1000 + i))
            deleted = prune_old_archives(ad, "fastapi_", keep=2)
            remaining = sorted(ad.glob("fastapi_*.log"))
            self.assertEqual(len(remaining), 2)
            self.assertEqual(len(deleted), 3)

    def test_dry_run_no_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "logs" / "fastapi.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text("x" * 100, encoding="utf-8")
            archive_dir = Path(tmp) / "logs" / "archive"
            did = rotate_fastapi_log(
                log_path,
                max_bytes=50,
                archive_dir=archive_dir,
                keep_archives=10,
                dry_run=True,
            )
            self.assertTrue(did)
            self.assertEqual(log_path.read_text(encoding="utf-8"), "x" * 100)
            self.assertFalse(archive_dir.exists())


if __name__ == "__main__":
    unittest.main()
