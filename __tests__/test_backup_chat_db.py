"""Tests for scripts/backup_chat_db.py."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.backup_chat_db import backup_chat_db, prune_old_backups


class BackupChatDbTests(unittest.TestCase):
    def test_backup_copies_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            src = base / "chat_logs.db"
            dest_dir = base / "backups"
            conn = sqlite3.connect(src)
            try:
                conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, x TEXT)")
                conn.execute("INSERT INTO t (x) VALUES ('hello')")
                conn.commit()
            finally:
                conn.close()

            out = backup_chat_db(src, dest_dir, max_files=10)
            self.assertTrue(out.is_file())
            rconn = sqlite3.connect(out)
            try:
                row = rconn.execute("SELECT x FROM t").fetchone()
            finally:
                rconn.close()
            self.assertEqual(row, ("hello",))

    def test_backup_missing_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            with self.assertRaises(FileNotFoundError):
                backup_chat_db(base / "missing.db", base / "backups", max_files=5)

    def test_prune_old_backups(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bd = Path(tmp)
            for i in range(4):
                p = bd / f"chat_logs_{i}.db"
                p.write_bytes(b"x")
                import os

                os.utime(p, (2000 + i, 2000 + i))
            deleted = prune_old_backups(bd, "chat_logs_", ".db", keep=2)
            remaining = list(bd.glob("chat_logs_*.db"))
            self.assertEqual(len(remaining), 2)
            self.assertEqual(len(deleted), 2)


if __name__ == "__main__":
    unittest.main()
