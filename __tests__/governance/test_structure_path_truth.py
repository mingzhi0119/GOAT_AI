from __future__ import annotations

from pathlib import Path

from __tests__.helpers.repo_root import repo_root


REPO_ROOT = repo_root(Path(__file__))

TARGETS = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "AGENTS.md",
    REPO_ROOT / "CLAUDE.md",
    REPO_ROOT / ".github" / "CODEOWNERS",
    *sorted((REPO_ROOT / "docs").rglob("*.md")),
    *sorted((REPO_ROOT / "docs").rglob("*.json")),
    *sorted((REPO_ROOT / "docs").rglob("*.yaml")),
    *sorted((REPO_ROOT / "docs").rglob("*.yml")),
    *sorted((REPO_ROOT / ".cursor" / "rules").glob("*.mdc")),
]

FORBIDDEN_SNIPPETS = [
    "docs/ENGINEERING_STANDARDS.md",
    "docs/DOMAIN.md",
    "docs/APPEARANCE.md",
    "docs/PROJECT_STATUS.md",
    "docs/ROADMAP.md",
    "docs/QUALITY_TRENDS.md",
    "docs/SECURITY.md",
    "docs/SECURITY_RESPONSE.md",
    "docs/OPERATIONS.md",
    "docs/BACKUP_RESTORE.md",
    "docs/ROLLBACK.md",
    "docs/RELEASE_GOVERNANCE.md",
    "docs/INCIDENT_TRIAGE.md",
    "docs/WSL_DEVELOPMENT.md",
    "docs/DESKTOP_CARGO_AUDIT_EXCEPTIONS.md",
    "docs/openapi.json",
    "docs/api.llm.yaml",
    "backend/config.py",
    "backend/dependencies.py",
    "backend/exception_handlers.py",
    "backend/http_security.py",
    "backend/otel_middleware.py",
    "backend/prometheus_metrics.py",
    "backend/readiness_service.py",
    "goat_ai/config.py",
    "goat_ai/ollama_client.py",
    "goat_ai/runtime_target.py",
    "goat_ai/clocks.py",
    "goat_ai/desktop_sidecar.py",
    "tools/check_api_contract_sync.py",
    "tools/generate_llm_api_yaml.py",
    "tools/regenerate_openapi_json.py",
    "tools/build_desktop_sidecar.py",
    "tools/desktop_smoke.py",
    "tools/write_desktop_release_provenance.py",
    "tools/backup_chat_db.py",
    "tools/exercise_recovery_drill.py",
    "tools/post_deploy_check.py",
    "tools/rotate_fastapi_log.py",
    "tools/build_release_bundle.py",
    "tools/exercise_release_rollback_drill.py",
    "tools/install_release_bundle.py",
    "tools/load_chat_smoke.py",
    "tools/quality_snapshot.py",
    "tools/run_pr_latency_gate.py",
    "tools/run_rag_eval.py",
    "tools/security_review_snapshot.py",
    "](../AGENTS.md)",
    "](../README.md)",
    "](../ops/observability/",
]


def test_structure_docs_and_rules_reference_canonical_paths() -> None:
    violations: list[str] = []
    for path in TARGETS:
        text = path.read_text(encoding="utf-8")
        for snippet in FORBIDDEN_SNIPPETS:
            if snippet in text:
                violations.append(
                    f"{path.relative_to(REPO_ROOT)} contains stale path `{snippet}`"
                )

    assert violations == [], (
        "Repo docs/rules should reference canonical industrial structure paths"
    )
