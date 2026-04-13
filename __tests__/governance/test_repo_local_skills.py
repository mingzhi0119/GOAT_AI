from __future__ import annotations

import re
from pathlib import Path

from __tests__.helpers.repo_root import repo_root


REPO_ROOT = repo_root(Path(__file__))
SKILLS_ROOT = REPO_ROOT / ".agents" / "skills"
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
FRONTMATTER_RE = re.compile(r"^---\n(?P<body>.*?)\n---\n", re.DOTALL)
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


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
    text = path.read_text(encoding="utf-8")
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
