from __future__ import annotations

from pathlib import Path

from __tests__.helpers.repo_root import repo_root


REPO_ROOT = repo_root(Path(__file__))


def test_api_reference_describes_object_store_boundary_for_persisted_blobs() -> None:
    api_reference = (REPO_ROOT / "docs" / "api" / "API_REFERENCE.md").read_text(
        encoding="utf-8"
    )

    for snippet in (
        "persisted through the configured object store using a canonical `storage_key`",
        "configured object store while SQLite keeps the metadata rows",
        "persists through the configured object store for the lifetime of the attachment id",
        "Resolves the payload by persisted `storage_key`",
    ):
        assert snippet in api_reference

    assert "GOAT_DATA_DIR/uploads/knowledge" not in api_reference
    assert "persists under `GOAT_DATA_DIR`" not in api_reference
