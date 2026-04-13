from __future__ import annotations

from pathlib import Path

from __tests__.helpers.repo_root import repo_root


REPO_ROOT = repo_root(Path(__file__))
SPECS_ROOT = REPO_ROOT / "docs" / "governance" / "specs"


def test_feature_specs_pilot_uses_a_narrow_allowed_file_set() -> None:
    assert SPECS_ROOT.is_dir()

    directories = sorted(path.name for path in SPECS_ROOT.iterdir() if path.is_dir())
    assert directories == [
        "_template",
        "governance-tooling-follow-ons",
        "project-memory-connectors-foundation",
        "workbench-multi-step-research",
    ]

    expected_files = {"plan.md", "spec.md", "tasks.md"}
    for directory in directories:
        files = {
            path.name for path in (SPECS_ROOT / directory).iterdir() if path.is_file()
        }
        assert files == expected_files


def test_feature_specs_docs_remain_explicitly_non_canonical() -> None:
    readme = (SPECS_ROOT / "README.md").read_text(encoding="utf-8")
    template_spec = (SPECS_ROOT / "_template" / "spec.md").read_text(encoding="utf-8")
    example_spec = (SPECS_ROOT / "governance-tooling-follow-ons" / "spec.md").read_text(
        encoding="utf-8"
    )
    task_two_spec = (
        SPECS_ROOT / "project-memory-connectors-foundation" / "spec.md"
    ).read_text(encoding="utf-8")
    task_one_spec = (
        SPECS_ROOT / "workbench-multi-step-research" / "spec.md"
    ).read_text(encoding="utf-8")

    assert "not a second governance system" in readme
    assert "ROADMAP.md" in readme
    assert "PROJECT_STATUS.md" in readme
    assert "AGENTS.md" in readme
    assert "repo-local skills" in readme
    assert "non-canonical working artifact" in template_spec
    assert "non-canonical working artifact" in example_spec
    assert "non-canonical working artifact" in task_two_spec
    assert "non-canonical working artifact" in task_one_spec
