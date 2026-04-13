from __future__ import annotations

from pathlib import Path

from __tests__.helpers.repo_root import repo_root


REPO_ROOT = repo_root(Path(__file__))


def test_phase16_storage_governance_docs_align_on_shipped_16c_and_16d() -> None:
    roadmap = (REPO_ROOT / "docs" / "governance" / "ROADMAP.md").read_text(
        encoding="utf-8"
    )
    project_status = (
        REPO_ROOT / "docs" / "governance" / "PROJECT_STATUS.md"
    ).read_text(encoding="utf-8")
    roadmap_archive = (
        REPO_ROOT / "docs" / "governance" / "ROADMAP_ARCHIVE.md"
    ).read_text(encoding="utf-8")
    decision_package = (
        REPO_ROOT / "docs" / "architecture" / "STORAGE_EVOLUTION_DECISION_PACKAGE.md"
    ).read_text(encoding="utf-8")

    assert (
        "Hosted runtime persistence after the landed object-store boundary"
        not in roadmap
    )
    assert "Phase 16C external object/file storage is now shipped" not in roadmap
    assert "#### Phase 16C: external object/file storage" not in roadmap
    assert "#### Phase 16D: Postgres-backed runtime persistence" not in roadmap

    assert "**16B/16C storage evolution:**" in project_status
    assert "**16D Postgres-backed runtime persistence:** complete" in project_status

    assert (
        "Historical note: the bullets immediately below preserve the labels"
        in roadmap_archive
    )
    assert "### Phase 16C storage closeout" in roadmap_archive
    assert "### Phase 16D runtime persistence closeout" in roadmap_archive

    assert "## Phase 16C landed decision" in decision_package
    assert "## Phase 16D landed decision" in decision_package
    assert "`storage_key`" in decision_package
    assert "`GOAT_OBJECT_STORE_ROOT`" in decision_package
    assert "## Remaining open decision topics (Phase 16D)" not in decision_package
