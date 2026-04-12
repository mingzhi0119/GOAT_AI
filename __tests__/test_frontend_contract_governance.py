from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_frontend_contract_generation_is_committed_and_wired_into_ci() -> None:
    package_json = json.loads(
        (REPO_ROOT / "frontend" / "package.json").read_text(encoding="utf-8")
    )
    ci_workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    generated_types = (
        REPO_ROOT / "frontend" / "src" / "api" / "generated" / "openapi.ts"
    )

    assert package_json["scripts"]["contract:generate"] == (
        "node ./scripts/generate-api-types.mjs"
    )
    assert package_json["scripts"]["contract:check"] == (
        "node ./scripts/generate-api-types.mjs --check"
    )
    assert "openapi-typescript" in package_json["devDependencies"]
    assert "npm run contract:check" in ci_workflow
    assert generated_types.is_file()


def test_frontend_browser_quality_gates_are_part_of_standard_ci() -> None:
    package_json = json.loads(
        (REPO_ROOT / "frontend" / "package.json").read_text(encoding="utf-8")
    )
    ci_workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    assert package_json["scripts"]["lint"] == "eslint ."
    assert package_json["scripts"]["bundle:check"] == (
        "node ./scripts/check-bundle-budget.mjs"
    )
    assert package_json["scripts"]["test:e2e"] == "playwright test"
    assert "@playwright/test" in package_json["devDependencies"]
    assert "eslint" in package_json["devDependencies"]
    assert "eslint-plugin-jsx-a11y" in package_json["devDependencies"]
    assert "npx playwright install --with-deps chromium" in ci_workflow
    assert "npm run lint" in ci_workflow
    assert "npm run bundle:check" in ci_workflow
    assert "npm run test:e2e" in ci_workflow
    assert (REPO_ROOT / "frontend" / "playwright.config.ts").is_file()
    assert (REPO_ROOT / "frontend" / "eslint.config.js").is_file()
    assert (REPO_ROOT / "frontend" / "e2e" / "protected-flows.spec.ts").is_file()


def test_frontend_types_docstring_points_to_generated_contract_source() -> None:
    types_file = (REPO_ROOT / "frontend" / "src" / "api" / "types.ts").read_text(
        encoding="utf-8"
    )

    assert "generated under `src/api/generated/openapi.ts`" in types_file
