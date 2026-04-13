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
