from __future__ import annotations

from pathlib import Path

from __tests__.helpers.repo_root import repo_root


REPO_ROOT = repo_root(Path(__file__))
STANDARDS_PATH = REPO_ROOT / "docs" / "standards" / "ENGINEERING_STANDARDS.md"

REQUIRED_HEADINGS = [
    "## 0B. Canonical Repository Layout",
    "## 0C. Industrial Score Gate Map",
]

REQUIRED_LAYOUT_SNIPPETS = [
    "`backend/`",
    "`frontend/`",
    "`goat_ai/`",
    "`tools/`",
    "`ops/`",
    "`docs/`",
    "`__tests__/`",
    "`scripts/`",
]

REQUIRED_DIMENSION_SNIPPETS = [
    "correctness",
    "testability",
    "maintainability",
    "readability",
    "architecture",
    "reliability",
    "performance",
    "security",
    "observability",
    "delivery maturity",
]


def test_engineering_standards_capture_repo_layout_and_score_guardrails() -> None:
    text = STANDARDS_PATH.read_text(encoding="utf-8")

    missing = [
        snippet
        for snippet in (
            *REQUIRED_HEADINGS,
            *REQUIRED_LAYOUT_SNIPPETS,
            *REQUIRED_DIMENSION_SNIPPETS,
        )
        if snippet not in text
    ]

    assert missing == [], (
        "Engineering standards must remain the canonical source for repo layout "
        f"and industrial score guardrails. Missing: {missing}"
    )
