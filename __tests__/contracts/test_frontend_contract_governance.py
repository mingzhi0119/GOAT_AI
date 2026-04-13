from __future__ import annotations

import json
from pathlib import Path

from __tests__.helpers.repo_root import repo_root

REPO_ROOT = repo_root(Path(__file__))


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


def test_frontend_runtime_api_parsers_stay_inside_src_api() -> None:
    package_json = json.loads(
        (REPO_ROOT / "frontend" / "package.json").read_text(encoding="utf-8")
    )
    runtime_schemas = (
        REPO_ROOT / "frontend" / "src" / "api" / "runtimeSchemas.ts"
    ).read_text(encoding="utf-8")
    system_api = (REPO_ROOT / "frontend" / "src" / "api" / "system.ts").read_text(
        encoding="utf-8"
    )
    code_sandbox_api = (
        REPO_ROOT / "frontend" / "src" / "api" / "codeSandbox.ts"
    ).read_text(encoding="utf-8")
    chat_api = (REPO_ROOT / "frontend" / "src" / "api" / "chat.ts").read_text(
        encoding="utf-8"
    )
    upload_api = (REPO_ROOT / "frontend" / "src" / "api" / "upload.ts").read_text(
        encoding="utf-8"
    )

    assert "zod" in package_json["dependencies"]
    assert "parseSystemFeaturesResponse" in runtime_schemas
    assert "parseGpuStatusResponse" in runtime_schemas
    assert "parseInferenceLatencyResponse" in runtime_schemas
    assert "parseDesktopDiagnosticsResponse" in runtime_schemas
    assert "parseModelsResponse" in runtime_schemas
    assert "parseModelCapabilitiesResponse" in runtime_schemas
    assert "parseHistorySessionListResponse" in runtime_schemas
    assert "parseHistorySessionDetailResponse" in runtime_schemas
    assert "parseMediaUploadResponse" in runtime_schemas
    assert "parseChatStreamEvent" in runtime_schemas
    assert "parseUploadStreamEvent" in runtime_schemas
    assert "parseCodeSandboxExecutionResponse" in runtime_schemas
    assert "parseCodeSandboxExecutionEventsResponse" in runtime_schemas
    assert "parseCodeSandboxLogStreamEvent" in runtime_schemas
    assert "return parseSystemFeaturesResponse(await resp.json())" in system_api
    assert "return parseGpuStatusResponse(await resp.json())" in system_api
    assert "return parseInferenceLatencyResponse(await resp.json())" in system_api
    assert "return parseDesktopDiagnosticsResponse(await resp.json())" in system_api
    assert (
        "return parseCodeSandboxExecutionResponse(await resp.json())"
        in code_sandbox_api
    )
    assert "return parseCodeSandboxExecutionEventsResponse(await resp.json())" in (
        code_sandbox_api
    )
    assert "parseCodeSandboxLogStreamEvent" in code_sandbox_api
    assert "parseChatStreamEvent" in chat_api
    assert "parseUploadStreamEvent" in upload_api


def test_frontend_json_api_adapters_do_not_use_unchecked_resp_json_casts() -> None:
    api_root = REPO_ROOT / "frontend" / "src" / "api"
    violations: list[str] = []

    for path in sorted(api_root.glob("*.ts")):
        if path.name == "errors.ts":
            continue
        text = path.read_text(encoding="utf-8")
        if "resp.json()) as " in text:
            violations.append(path.relative_to(REPO_ROOT).as_posix())

    assert violations == []


def test_future_workbench_frontend_adapters_must_use_shared_runtime_boundaries() -> (
    None
):
    api_root = REPO_ROOT / "frontend" / "src" / "api"

    for path in sorted(api_root.glob("*.ts")):
        text = path.read_text(encoding="utf-8")
        if "/api/workbench" not in text:
            continue

        assert "runtimeSchemas" in text
        assert "from './types'" in text or 'from "./types"' in text
        assert "from './generated/openapi'" not in text
        assert 'from "./generated/openapi"' not in text
        assert "resp.json()) as " not in text
