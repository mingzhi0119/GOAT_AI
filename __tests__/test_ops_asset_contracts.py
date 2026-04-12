from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_deploy_scripts_use_factory_entrypoint() -> None:
    deploy_sh = (REPO_ROOT / "deploy.sh").read_text(encoding="utf-8")
    deploy_ps1 = (REPO_ROOT / "deploy.ps1").read_text(encoding="utf-8")

    assert "server:create_app" in deploy_sh
    assert "--factory" in deploy_sh
    assert '"server:create_app"' in deploy_ps1
    assert '"--factory"' in deploy_ps1


def test_goat_service_uses_supported_logs_and_factory_entrypoint() -> None:
    service = (REPO_ROOT / "goat-ai.service").read_text(encoding="utf-8")

    assert "ExecStartPre=/usr/bin/mkdir -p %h/GOAT_AI/logs" in service
    assert "server:create_app" in service
    assert "--factory" in service
    assert "logs/fastapi.log" in service


def test_watchdog_phase0_and_local_ollama_scripts_align_with_supported_ops_contract() -> (
    None
):
    healthcheck = (REPO_ROOT / "scripts" / "healthcheck.sh").read_text(encoding="utf-8")
    watchdog = (REPO_ROOT / "scripts" / "watchdog.sh").read_text(encoding="utf-8")
    phase0 = (REPO_ROOT / "phase0_check.sh").read_text(encoding="utf-8")
    start_ollama = (REPO_ROOT / "scripts" / "start_ollama_local.sh").read_text(
        encoding="utf-8"
    )

    assert "GOAT_HEALTH_URL:=http://127.0.0.1:62606/api/health" in healthcheck
    assert 'LOG="${GOAT_WATCHDOG_LOG:-$PROJECT_DIR/logs/watchdog.log}"' in watchdog
    assert 'mkdir -p "$(dirname "$LOG")"' in watchdog

    assert "Need Node 24.x" in phase0
    assert "npm ci --silent" in phase0
    assert "server:create_app --factory" in phase0
    assert "logs/fastapi.log" in phase0
    assert "logs/fastapi.pid" in phase0

    assert (
        'OLLAMA_BASE_URL_VALUE="${OLLAMA_BASE_URL:-${OLLAMA_HOST:-http://127.0.0.1:11435}}"'
        in start_ollama
    )
    assert 'OLLAMA_HOST="${OLLAMA_BASE_URL_VALUE}"' in start_ollama


def test_release_docs_and_status_match_current_truth() -> None:
    release_doc = (REPO_ROOT / "docs" / "RELEASE_GOVERNANCE.md").read_text(
        encoding="utf-8"
    )
    rollback_doc = (REPO_ROOT / "docs" / "ROLLBACK.md").read_text(encoding="utf-8")
    operations_doc = (REPO_ROOT / "docs" / "OPERATIONS.md").read_text(encoding="utf-8")
    project_status = (REPO_ROOT / "docs" / "PROJECT_STATUS.md").read_text(
        encoding="utf-8"
    )

    assert "`STAGING_BASE_URL`" in release_doc
    assert "`PRODUCTION_BASE_URL`" in release_doc
    assert "immutable bundle" in release_doc
    assert "promotion evidence" in release_doc
    assert "exercise_release_rollback_drill" in rollback_doc
    assert "python -m tools.run_pr_latency_gate" in operations_doc
    assert "<app_log_dir>/desktop-shell.log" in operations_doc
    assert "P0, P1, and P2 are complete" not in project_status
    assert "artifact-first staged release governance workflow" in project_status
