from __future__ import annotations

from pathlib import Path

from __tests__.helpers.repo_root import repo_root


REPO_ROOT = repo_root(Path(__file__))
AGENTS_PATH = REPO_ROOT / "AGENTS.md"
POLICY_PATH = REPO_ROOT / "docs" / "governance" / "CODEX_LOGS.md"
LOGS_ROOT = REPO_ROOT / "docs" / "governance" / "codex-logs"


def test_agents_guidance_requires_codex_logs_for_code_changes() -> None:
    text = AGENTS_PATH.read_text(encoding="utf-8")

    for snippet in (
        "docs/governance/CODEX_LOGS.md",
        "Read-only review work is exempt",
        "Long-running work logs once per commit",
        "small tasks log once per conversation round-trip",
    ):
        assert snippet in text


def test_codex_log_policy_defines_required_location_and_rules() -> None:
    text = POLICY_PATH.read_text(encoding="utf-8")

    for snippet in (
        "docs/governance/codex-logs/",
        "YYYY-MM.md",
        "Read-only review work is exempt.",
        "Every code-changing task must record at least one log entry.",
        "Long-running tasks record one entry per commit.",
        "Small tasks record one entry per conversation round-trip.",
        "Codex logs capture execution history for code-changing work.",
    ):
        assert snippet in text


def test_codex_logs_bootstrap_with_a_monthly_log_file() -> None:
    assert LOGS_ROOT.is_dir()

    monthly_logs = sorted(path.name for path in LOGS_ROOT.glob("????-??.md"))
    assert "2026-04.md" in monthly_logs

    bootstrap_log = (LOGS_ROOT / "2026-04.md").read_text(encoding="utf-8")
    for snippet in (
        "Codex log policy bootstrap",
        "AGENTS.md",
        "docs/governance/CODEX_LOGS.md",
        "__tests__/governance/test_codex_logs_governance.py",
    ):
        assert snippet in bootstrap_log
