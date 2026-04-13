from __future__ import annotations

from pathlib import Path

from __tests__.helpers.repo_root import repo_root


REPO_ROOT = repo_root(Path(__file__))


def test_storage_ops_docs_cover_local_and_remote_object_store_modes() -> None:
    operations = (REPO_ROOT / "docs" / "operations" / "OPERATIONS.md").read_text(
        encoding="utf-8"
    )
    backup_restore = (
        REPO_ROOT / "docs" / "operations" / "BACKUP_RESTORE.md"
    ).read_text(encoding="utf-8")
    rollback = (REPO_ROOT / "docs" / "operations" / "ROLLBACK.md").read_text(
        encoding="utf-8"
    )

    for snippet in (
        "`GOAT_OBJECT_STORE_BACKEND`",
        "`GOAT_OBJECT_STORE_ROOT`",
        "`GOAT_OBJECT_STORE_BUCKET`",
        "`GOAT_OBJECT_STORE_S3_ADDRESSING_STYLE`",
        "defaults to `GOAT_DATA_DIR`",
        "When `GOAT_OBJECT_STORE_BACKEND=local`, snapshot `GOAT_OBJECT_STORE_ROOT`",
        "When `GOAT_OBJECT_STORE_BACKEND=s3`, pair the SQLite backup",
    ):
        assert snippet in operations

    for snippet in (
        "`GOAT_OBJECT_STORE_ROOT`",
        "`s3` backend: capture a provider-native snapshot/version set",
        "expected keyspace before treating the backup set as complete",
        "storage_key",
    ):
        assert snippet in backup_restore

    for snippet in (
        "restoring `GOAT_OBJECT_STORE_ROOT`",
        "restoring the matching bucket/prefix",
        "snapshot or version set",
        "A ref or bundle rollback does not restore remote objects by itself.",
    ):
        assert snippet in rollback
