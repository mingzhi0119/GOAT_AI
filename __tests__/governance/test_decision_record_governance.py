from __future__ import annotations

from pathlib import Path

from __tests__.helpers.repo_root import repo_root


REPO_ROOT = repo_root(Path(__file__))
DECISIONS_ROOT = REPO_ROOT / "docs" / "decisions"
README_PATH = DECISIONS_ROOT / "README.md"
RECORD_TEMPLATE_PATH = DECISIONS_ROOT / "templates" / "decision-record.md"
PACKAGE_TEMPLATE_PATH = DECISIONS_ROOT / "templates" / "decision-package.md"


def test_decision_record_entrypoint_indexes_templates_and_examples() -> None:
    text = README_PATH.read_text(encoding="utf-8")

    for snippet in (
        "canonical entrypoint",
        "decision record",
        "decision package",
        "templates/decision-record.md",
        "templates/decision-package.md",
        "../architecture/WORKBENCH_TERMINOLOGY_DECISION.md",
        "../architecture/STORAGE_EVOLUTION_DECISION_PACKAGE.md",
        "../architecture/EXTERNAL_OBJECT_STORAGE_DECISION_PACKAGE.md",
        "AGENTS.md",
        "ENGINEERING_STANDARDS.md",
    ):
        assert snippet in text


def test_decision_record_template_has_required_sections() -> None:
    text = RECORD_TEMPLATE_PATH.read_text(encoding="utf-8")

    for snippet in (
        "## Purpose",
        "## Context",
        "## Decision",
        "## Options considered",
        "## Consequences",
        "## Rollback or reversal implications",
        "## Validation and proof",
        "## Related artifacts",
    ):
        assert snippet in text


def test_decision_package_template_has_required_sections() -> None:
    text = PACKAGE_TEMPLATE_PATH.read_text(encoding="utf-8")

    for snippet in (
        "## Purpose",
        "## Context",
        "## Fixed constraints",
        "## Decision",
        "## Options considered",
        "## Compatibility strategy",
        "## Migration or rollout sequence",
        "## Rollback strategy",
        "## Validation and proof",
        "## Open questions",
        "## Related artifacts",
    ):
        assert snippet in text


def test_external_object_storage_package_is_indexed_and_uses_required_sections() -> (
    None
):
    package_path = (
        REPO_ROOT
        / "docs"
        / "architecture"
        / "EXTERNAL_OBJECT_STORAGE_DECISION_PACKAGE.md"
    )
    text = package_path.read_text(encoding="utf-8")

    for snippet in (
        "# External Object Storage Decision Package",
        "## Purpose",
        "## Context",
        "## Fixed constraints",
        "## Decision",
        "## Options considered",
        "## Compatibility strategy",
        "## Migration or rollout sequence",
        "## Rollback strategy",
        "## Validation and proof",
        "## Open questions",
        "## Related artifacts",
        "GOAT_OBJECT_STORE_BACKEND",
        "storage_key",
    ):
        assert snippet in text


def test_phase16_storage_docs_align_across_live_and_archive_views() -> None:
    roadmap = (REPO_ROOT / "docs" / "governance" / "ROADMAP.md").read_text(
        encoding="utf-8"
    )
    status = (REPO_ROOT / "docs" / "governance" / "PROJECT_STATUS.md").read_text(
        encoding="utf-8"
    )
    archive = (REPO_ROOT / "docs" / "governance" / "ROADMAP_ARCHIVE.md").read_text(
        encoding="utf-8"
    )

    assert "Phase 16C external object/file storage is now shipped." in roadmap
    assert "**16B/16C storage evolution:** complete" in status
    assert "### Phase 16C storage closeout" in archive
    assert "The historical 16C checklist covered:" in archive
