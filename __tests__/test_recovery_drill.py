from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest

from scripts.exercise_recovery_drill import (
    _sqlite_integrity_check,
    exercise_recovery_drill,
)


def _seed_db(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE sessions (id TEXT PRIMARY KEY, owner_id TEXT)")
        conn.execute(
            "CREATE TABLE session_messages (id INTEGER PRIMARY KEY, session_id TEXT, body TEXT)"
        )
        conn.execute("INSERT INTO sessions (id, owner_id) VALUES ('s-1', 'owner-1')")
        conn.execute(
            "INSERT INTO session_messages (session_id, body) VALUES ('s-1', 'hello')"
        )
        conn.commit()


def test_exercise_recovery_drill_performs_backup_restore_and_rollback() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        root = Path(tmp)
        src = root / "chat_logs.db"
        backup_dir = root / "backups"
        work_dir = root / "drill"
        _seed_db(src)

        result = exercise_recovery_drill(
            src=src,
            backup_dir=backup_dir,
            max_files=4,
            required_tables=["sessions", "session_messages"],
            work_dir=work_dir,
        )

        assert Path(result.backup_path).is_file()
        assert Path(result.restore_target_path).is_file()
        assert Path(result.rollback_copy_path).is_file()
        assert result.backup_sha256 == result.restored_sha256
        assert result.rolled_back_sha256 != ""
        assert result.verified_tables == ["sessions", "session_messages"]
        assert _sqlite_integrity_check(Path(result.restore_target_path)) == "ok"


def test_exercise_recovery_drill_rejects_missing_required_tables() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        root = Path(tmp)
        src = root / "chat_logs.db"
        backup_dir = root / "backups"
        with sqlite3.connect(src) as conn:
            conn.execute("CREATE TABLE sessions (id TEXT PRIMARY KEY)")
            conn.commit()

        with pytest.raises(ValueError, match="missing required tables"):
            exercise_recovery_drill(
                src=src,
                backup_dir=backup_dir,
                max_files=4,
                required_tables=["sessions", "session_messages"],
                work_dir=root / "drill",
            )


def test_sqlite_integrity_check_surfaces_corruption_signal() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        broken = Path(tmp) / "broken.db"
        broken.write_bytes(b"not-a-real-sqlite-db")

        with pytest.raises(sqlite3.DatabaseError):
            _sqlite_integrity_check(broken)
