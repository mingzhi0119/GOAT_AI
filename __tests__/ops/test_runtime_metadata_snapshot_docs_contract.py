from __future__ import annotations

from pathlib import Path

from __tests__.helpers.repo_root import repo_root


REPO_ROOT = repo_root(Path(__file__))


def test_runtime_metadata_snapshot_docs_reference_export_import_and_parity_tooling() -> (
    None
):
    decision_package = (
        REPO_ROOT
        / "docs"
        / "architecture"
        / "POSTGRES_RUNTIME_PERSISTENCE_DECISION_PACKAGE.md"
    ).read_text(encoding="utf-8")
    backup_restore = (
        REPO_ROOT / "docs" / "operations" / "BACKUP_RESTORE.md"
    ).read_text(encoding="utf-8")

    for snippet in (
        "backend/services/runtime_metadata_inventory.py",
        "python -m tools.ops.upgrade_runtime_postgres_schema",
        "python -m tools.ops.export_runtime_metadata_snapshot",
        "python -m tools.ops.import_runtime_metadata_snapshot",
        "python -m tools.ops.check_runtime_metadata_parity",
    ):
        assert snippet in decision_package

    for snippet in (
        "python -m tools.ops.upgrade_runtime_postgres_schema",
        "python -m tools.ops.export_runtime_metadata_snapshot",
        "python -m tools.ops.import_runtime_metadata_snapshot",
        "python -m tools.ops.check_runtime_metadata_parity",
        "deterministic runtime metadata snapshot",
        "full governed table family",
    ):
        assert snippet in backup_restore
