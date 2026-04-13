from __future__ import annotations

import re
from pathlib import Path

from __tests__.helpers.repo_root import repo_root
from __tests__.ops.test_observability_asset_contract import APPROVED_SURFACE_PATHS


REPO_ROOT = repo_root(Path(__file__))
SKILLS_ROOT = REPO_ROOT / ".agents" / "skills"
README_PATH = SKILLS_ROOT / "README.md"
AGENTS_PATH = REPO_ROOT / "AGENTS.md"
ROADMAP_PATH = REPO_ROOT / "docs" / "governance" / "ROADMAP.md"
REQUIRED_SKILLS = {
    "goat-api-contract-proof",
    "goat-ci-surface-router",
    "goat-desktop-release-evidence",
    "goat-engineering-audit",
    "goat-governance-sync",
    "goat-observability-contract-proof",
    "goat-workbench-authz-proof",
    "wsl-linux-build",
    "wsl-linux-ops-checks",
    "wsl-linux-rust-desktop",
}
GOAT_SKILLS = {name for name in REQUIRED_SKILLS if name.startswith("goat-")}
WSL_SKILLS = {name for name in REQUIRED_SKILLS if name.startswith("wsl-")}
HIGH_FREQUENCY_GOAT_SKILLS = GOAT_SKILLS - {"goat-governance-sync"}
FRONTMATTER_RE = re.compile(r"^---\n(?P<body>.*?)\n---\n", re.DOTALL)
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
ALLOW_IMPLICIT_RE = re.compile(r"allow_implicit_invocation:\s*(true|false)")
SKILL_TOKEN_RE = re.compile(r"\$([a-z0-9-]+)")


def _skill_dirs() -> list[Path]:
    return sorted(path for path in SKILLS_ROOT.iterdir() if path.is_dir())


def _parse_frontmatter(skill_path: Path) -> dict[str, str]:
    text = skill_path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    assert match is not None, f"{skill_path.relative_to(REPO_ROOT)} missing frontmatter"
    fields: dict[str, str] = {}
    for line in match.group("body").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def _iter_markdown_links(path: Path) -> list[str]:
    return _iter_markdown_link_targets(path.read_text(encoding="utf-8"))


def _iter_markdown_link_targets(text: str) -> list[str]:
    targets: list[str] = []
    for target in MARKDOWN_LINK_RE.findall(text):
        cleaned = target.strip()
        if cleaned.startswith(("http://", "https://", "mailto:", "#")):
            continue
        if cleaned.startswith("<") and cleaned.endswith(">"):
            cleaned = cleaned[1:-1]
        cleaned = cleaned.split("#", 1)[0]
        if cleaned:
            targets.append(cleaned)
    return targets


def _resolve_repo_relative_targets(markdown_path: Path) -> set[str]:
    return {
        (markdown_path.parent / target).resolve().relative_to(REPO_ROOT).as_posix()
        for target in _iter_markdown_links(markdown_path)
    }


def _extract_markdown_section(path: Path, heading: str, *, level: int = 2) -> str:
    text = path.read_text(encoding="utf-8")
    marker = f"{'#' * level} {heading}\n\n"
    start = text.index(marker) + len(marker)
    next_marker = f"\n{'#' * level} "
    end = text.find(next_marker, start)
    if end == -1:
        return text[start:]
    return text[start:end]


def _parse_allow_implicit_invocation(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    match = ALLOW_IMPLICIT_RE.search(text)
    assert match is not None, (
        f"{path.relative_to(REPO_ROOT)} missing allow_implicit_invocation"
    )
    return match.group(1) == "true"


def test_repo_local_skill_inventory_and_metadata() -> None:
    existing = {path.name for path in _skill_dirs()}
    missing = sorted(REQUIRED_SKILLS - existing)
    assert not missing, f"Missing required repo-local skills: {missing}"

    for skill_dir in _skill_dirs():
        skill_path = skill_dir / "SKILL.md"
        openai_yaml = skill_dir / "agents" / "openai.yaml"
        assert skill_path.is_file(), f"{skill_dir.name} missing SKILL.md"
        assert openai_yaml.is_file(), f"{skill_dir.name} missing agents/openai.yaml"

        frontmatter = _parse_frontmatter(skill_path)
        assert frontmatter.get("name") == skill_dir.name, (
            f"{skill_dir.name} frontmatter name should match directory name"
        )
        assert frontmatter.get("description"), (
            f"{skill_dir.name} frontmatter must include description"
        )

        openai_text = openai_yaml.read_text(encoding="utf-8")
        for required_snippet in (
            "display_name:",
            "short_description:",
            "default_prompt:",
            "allow_implicit_invocation:",
        ):
            assert required_snippet in openai_text, (
                f"{openai_yaml.relative_to(REPO_ROOT)} missing `{required_snippet}`"
            )


def test_repo_local_skill_markdown_links_resolve() -> None:
    markdown_paths = sorted(SKILLS_ROOT.rglob("*.md"))
    assert markdown_paths, "Expected repo-local skill markdown files to exist"

    violations: list[str] = []
    for markdown_path in markdown_paths:
        for target in _iter_markdown_links(markdown_path):
            resolved = (markdown_path.parent / target).resolve()
            if not resolved.exists():
                violations.append(f"{markdown_path.relative_to(REPO_ROOT)} -> {target}")

    assert not violations, (
        "Repo-local skill markdown should only contain resolvable repo-relative links"
    )


def test_repo_local_skill_readme_indexes_required_skills_by_bucket() -> None:
    governance_section = _extract_markdown_section(
        README_PATH, "Governance and proof skills"
    )
    execution_section = _extract_markdown_section(
        README_PATH, "Execution-layer helpers"
    )

    governance_skills = {
        target.split("/", 1)[0]
        for target in _iter_markdown_link_targets(governance_section)
        if target.endswith("/SKILL.md")
    }
    execution_skills = {
        target.split("/", 1)[0]
        for target in _iter_markdown_link_targets(execution_section)
        if target.endswith("/SKILL.md")
    }

    assert governance_skills == GOAT_SKILLS
    assert execution_skills == WSL_SKILLS


def test_repo_local_skill_readme_exposes_high_frequency_dry_runs() -> None:
    dry_run_section = _extract_markdown_section(README_PATH, "High-frequency dry runs")
    dry_run_targets = set(_iter_markdown_link_targets(dry_run_section))
    expected = {
        f"{skill_name}/references/dry-run-examples.md"
        for skill_name in HIGH_FREQUENCY_GOAT_SKILLS
    }
    assert dry_run_targets == expected


def test_repo_local_goat_skill_policy_flags_match_expected_invocation_rules() -> None:
    for skill_name in GOAT_SKILLS:
        policy_path = SKILLS_ROOT / skill_name / "agents" / "openai.yaml"
        allow_implicit = _parse_allow_implicit_invocation(policy_path)
        assert allow_implicit is (skill_name != "goat-governance-sync"), (
            f"{policy_path.relative_to(REPO_ROOT)} allow_implicit_invocation drifted"
        )


def test_high_frequency_goat_skills_have_dry_run_examples() -> None:
    for skill_name in HIGH_FREQUENCY_GOAT_SKILLS:
        skill_path = SKILLS_ROOT / skill_name / "SKILL.md"
        dry_run_path = SKILLS_ROOT / skill_name / "references" / "dry-run-examples.md"

        assert dry_run_path.is_file(), f"{dry_run_path.relative_to(REPO_ROOT)} missing"

        skill_text = skill_path.read_text(encoding="utf-8")
        assert "## Dry-Run Examples" in skill_text
        assert "references/dry-run-examples.md" in skill_text

        dry_run_text = dry_run_path.read_text(encoding="utf-8")
        for snippet in (
            "## Example 1",
            "## Example 2",
            "User asks:",
            "First moves:",
            "Validate with:",
        ):
            assert snippet in dry_run_text, (
                f"{dry_run_path.relative_to(REPO_ROOT)} missing `{snippet}`"
            )


def test_agents_guidance_mentions_repo_skill_layers_and_entry_points() -> None:
    text = AGENTS_PATH.read_text(encoding="utf-8")
    for snippet in (
        "Repo-local `goat-*` skills",
        "Treat the `wsl-*` skills as execution helpers",
        "$goat-engineering-audit",
        "$goat-api-contract-proof",
        "$goat-ci-surface-router",
        "$goat-desktop-release-evidence",
        "$goat-workbench-authz-proof",
        "$goat-observability-contract-proof",
        "$goat-governance-sync",
    ):
        assert snippet in text

    unknown = sorted(
        {
            token
            for token in SKILL_TOKEN_RE.findall(text)
            if token.startswith(("goat-", "wsl-")) and token not in REQUIRED_SKILLS
        }
    )
    assert not unknown, f"AGENTS.md references unknown repo-local skills: {unknown}"


def test_roadmap_repo_native_skill_section_preserves_layering() -> None:
    section = _extract_markdown_section(
        ROADMAP_PATH, "Repository-native Skills and Agent Automation", level=3
    )
    assert (
        "`wsl-linux-build`, `wsl-linux-ops-checks`, and `wsl-linux-rust-desktop` remain"
        in section
    )
    assert (
        "the new `goat-*` skills sit above them as governance/proof workflows"
        in section
    )


def test_targeted_skills_keep_required_truth_sources_and_validation_clues() -> None:
    required_skill_snippets = {
        SKILLS_ROOT / "goat-api-contract-proof" / "SKILL.md": [
            "python -m tools.contracts.check_api_contract_sync",
            "npm run contract:check",
        ],
        SKILLS_ROOT / "goat-workbench-authz-proof" / "SKILL.md": [
            "/api/system/features",
            "__tests__/contracts/",
        ],
        SKILLS_ROOT / "goat-observability-contract-proof" / "SKILL.md": [
            "__tests__/ops/test_observability_asset_contract.py",
            "backend-heavy",
        ],
    }

    for path, snippets in required_skill_snippets.items():
        text = path.read_text(encoding="utf-8")
        for snippet in snippets:
            assert snippet in text, f"{path.relative_to(REPO_ROOT)} missing `{snippet}`"


def test_authz_truth_sources_include_scope_and_gate_reason_files() -> None:
    authz_truth_sources = (
        SKILLS_ROOT
        / "goat-workbench-authz-proof"
        / "references"
        / "authz-truth-sources.md"
    )
    targets = _resolve_repo_relative_targets(authz_truth_sources)
    required = {
        "goat_ai/config/feature_gates.py",
        "goat_ai/config/feature_gate_reasons.py",
        "backend/domain/scope_catalog.py",
        "backend/models/system.py",
    }
    assert required <= targets


def test_observability_approved_surfaces_reference_matches_contract_test_surface() -> (
    None
):
    approved_surfaces = (
        SKILLS_ROOT
        / "goat-observability-contract-proof"
        / "references"
        / "approved-surfaces.md"
    )
    actual = _resolve_repo_relative_targets(approved_surfaces)
    expected = {
        path.relative_to(REPO_ROOT).as_posix() for path in APPROVED_SURFACE_PATHS
    }
    assert actual == expected
