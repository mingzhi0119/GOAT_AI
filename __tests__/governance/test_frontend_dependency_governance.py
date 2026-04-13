from __future__ import annotations

import json
from pathlib import Path

from __tests__.helpers.repo_root import repo_root


REPO_ROOT = repo_root(Path(__file__))
FRONTEND_ROOT = REPO_ROOT / "frontend"
PACKAGE_JSON_PATH = FRONTEND_ROOT / "package.json"
PACKAGE_LOCK_PATH = FRONTEND_ROOT / "package-lock.json"
CI_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"
DEPCRUISE_CONFIG_PATH = FRONTEND_ROOT / ".dependency-cruiser.cjs"


def test_frontend_dependency_guardrails_are_wired_into_repo_truth() -> None:
    package_json = json.loads(PACKAGE_JSON_PATH.read_text(encoding="utf-8"))
    ci_workflow = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    config_text = DEPCRUISE_CONFIG_PATH.read_text(encoding="utf-8")
    package_lock_text = PACKAGE_LOCK_PATH.read_text(encoding="utf-8")

    assert package_json["scripts"]["depcruise"] == (
        "depcruise --config .dependency-cruiser.cjs src"
    )
    assert "dependency-cruiser" in package_json["devDependencies"]
    assert "dependency-cruiser" in package_lock_text
    assert "npm run depcruise" in ci_workflow

    for snippet in (
        "no-circular",
        "api-inward-only",
        "hooks-no-components",
        "utils-no-hooks-or-components",
        "generated-contracts-stay-behind-api",
    ):
        assert snippet in config_text


def test_frontend_network_calls_stay_inside_src_api() -> None:
    violations: list[str] = []
    for path in sorted((FRONTEND_ROOT / "src").rglob("*.ts*")):
        relative = path.relative_to(FRONTEND_ROOT).as_posix()
        if relative.startswith("src/api/") or "/__tests__/" in relative:
            continue

        text = path.read_text(encoding="utf-8")
        if "fetch(" in text:
            violations.append(relative)

    assert violations == [], "frontend network calls must stay inside src/api"
