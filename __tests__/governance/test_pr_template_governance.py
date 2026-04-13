from __future__ import annotations

from pathlib import Path

from __tests__.helpers.repo_root import repo_root


REPO_ROOT = repo_root(Path(__file__))
PR_TEMPLATE_PATH = REPO_ROOT / ".github" / "pull_request_template.md"


def test_pr_template_keeps_governance_prompts_for_risky_changes() -> None:
    text = PR_TEMPLATE_PATH.read_text(encoding="utf-8")

    for snippet in (
        "## Summary",
        "## User-visible behavior",
        "## Decision And Risk",
        "Decision artifact link",
        "Trade-offs / non-goals",
        "Rollback / failure surface",
        "Proof links",
        "## Testing",
    ):
        assert snippet in text
