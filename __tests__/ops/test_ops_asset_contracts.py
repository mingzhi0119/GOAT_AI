from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current.parent, *current.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise RuntimeError("Could not locate repository root from test path.")


REPO_ROOT = _repo_root()


def test_root_entrypoints_are_not_part_of_the_supported_ops_surface() -> None:
    assert not (REPO_ROOT / "deploy.sh").exists()
    assert not (REPO_ROOT / "deploy.ps1").exists()
    assert not (REPO_ROOT / "phase0_check.sh").exists()


def test_canonical_deploy_scripts_use_factory_entrypoint() -> None:
    deploy_sh = (REPO_ROOT / "ops" / "deploy" / "deploy.sh").read_text(encoding="utf-8")
    deploy_ps1 = (REPO_ROOT / "ops" / "deploy" / "deploy.ps1").read_text(
        encoding="utf-8"
    )

    assert "server:create_app" in deploy_sh
    assert "--factory" in deploy_sh
    assert '"server:create_app"' in deploy_ps1
    assert '"--factory"' in deploy_ps1


def test_goat_service_uses_supported_logs_and_factory_entrypoint() -> None:
    service = (REPO_ROOT / "ops" / "systemd" / "goat-ai.service").read_text(
        encoding="utf-8"
    )

    assert (
        "ExecStartPre=/usr/bin/mkdir -p %h/GOAT_AI/var/logs %h/GOAT_AI/var/data"
        in service
    )
    assert "Environment=GOAT_RUNTIME_ROOT=%h/GOAT_AI/var" in service
    assert "Environment=GOAT_LOG_DIR=%h/GOAT_AI/var/logs" in service
    assert "server:create_app" in service
    assert "--factory" in service
    assert "var/logs/fastapi.log" in service
    assert "start_ollama_local.sh" not in service


def test_watchdog_phase0_and_school_ollama_assets_align_with_supported_ops_contract() -> (
    None
):
    deploy_sh = (REPO_ROOT / "ops" / "deploy" / "deploy.sh").read_text(encoding="utf-8")
    healthcheck = (REPO_ROOT / "ops" / "verification" / "healthcheck.sh").read_text(
        encoding="utf-8"
    )
    watchdog = (REPO_ROOT / "ops" / "verification" / "watchdog.sh").read_text(
        encoding="utf-8"
    )
    phase0 = (REPO_ROOT / "ops" / "verification" / "phase0_check.sh").read_text(
        encoding="utf-8"
    )
    school_service = (
        REPO_ROOT / "ops" / "systemd" / "goat-ai.school-ubuntu.service"
    ).read_text(encoding="utf-8")
    start_ollama = (
        REPO_ROOT / "scripts" / "ollama" / "start_ollama_local.sh"
    ).read_text(encoding="utf-8")

    assert "GOAT_HEALTH_URL:=http://127.0.0.1:62606/api/health" in healthcheck
    assert 'GOAT_RUNTIME_ROOT="${GOAT_RUNTIME_ROOT:-$PROJECT_DIR/var}"' in watchdog
    assert 'GOAT_LOG_DIR="${GOAT_LOG_DIR:-$GOAT_RUNTIME_ROOT/logs}"' in watchdog
    assert 'LOG="${GOAT_WATCHDOG_LOG:-$GOAT_LOG_DIR/watchdog.log}"' in watchdog
    assert 'mkdir -p "$(dirname "$LOG")"' in watchdog
    assert "bash ops/deploy/deploy.sh" in watchdog

    assert "Need Node 24.x" in phase0
    assert "npm ci --silent" in phase0
    assert "server:create_app --factory" in phase0
    assert "var/logs/fastapi.log" in phase0
    assert "var/logs/fastapi.pid" in phase0

    assert (
        'GOAT_USE_SCHOOL_OLLAMA_LOCAL="${GOAT_USE_SCHOOL_OLLAMA_LOCAL:-0}"' in deploy_sh
    )
    assert 'GOAT_OLLAMA_PROFILE="${GOAT_OLLAMA_PROFILE:-}"' in deploy_sh
    assert 'PRIMARY_DOTENV_PATH="${PROJECT_DIR}/.env"' in deploy_sh
    assert 'SCHOOL_DOTENV_PATH="${PROJECT_DIR}/.env.school-ubuntu"' in deploy_sh
    assert "read_first_dotenv_value() {" in deploy_sh
    assert "school_ollama_local_enabled() {" in deploy_sh
    assert "School Ubuntu Ollama profile enabled" in deploy_sh
    assert '[ ! -f "${PROJECT_DIR}/scripts/ollama/start_ollama_local.sh" ]' in deploy_sh
    assert 'bash "${PROJECT_DIR}/scripts/ollama/start_ollama_local.sh"' in deploy_sh
    assert (
        '_dotenv_school_switch="$(read_first_dotenv_value "GOAT_USE_SCHOOL_OLLAMA_LOCAL" "${SCHOOL_DOTENV_PATH}" "${PRIMARY_DOTENV_PATH}")"'
        in deploy_sh
    )
    assert (
        '_dotenv_ollama_profile="$(read_first_dotenv_value "GOAT_OLLAMA_PROFILE" "${SCHOOL_DOTENV_PATH}" "${PRIMARY_DOTENV_PATH}")"'
        in deploy_sh
    )
    assert "_goat_systemd_restart goat-ai.school-ubuntu" in deploy_sh
    assert 'SELECTED_SYSTEMD_UNIT="goat-ai.school-ubuntu"' in deploy_sh
    assert 'systemctl --user stop "${SELECTED_SYSTEMD_UNIT}"' in deploy_sh
    assert (
        'GOAT_USE_SCHOOL_OLLAMA_LOCAL="${GOAT_USE_SCHOOL_OLLAMA_LOCAL}" \\' in deploy_sh
    )
    assert 'GOAT_OLLAMA_PROFILE="${GOAT_OLLAMA_PROFILE}" \\' in deploy_sh
    assert '[ "${EFFECTIVE_OLLAMA_URL}" = "${LOCAL_OLLAMA_URL}" ]' not in deploy_sh

    assert (
        "ExecStartPre=/usr/bin/bash %h/GOAT_AI/scripts/ollama/start_ollama_local.sh"
        in school_service
    )
    assert "Environment=GOAT_USE_SCHOOL_OLLAMA_LOCAL=1" in school_service
    assert "EnvironmentFile=-%h/GOAT_AI/.env.school-ubuntu" in school_service

    assert (
        'OLLAMA_BASE_URL_VALUE="${OLLAMA_BASE_URL:-${OLLAMA_HOST:-http://127.0.0.1:11435}}"'
        in start_ollama
    )
    assert 'OLLAMA_HOST="${OLLAMA_BASE_URL_VALUE}"' in start_ollama
    assert "scripts/ollama/ollama_local.sh" in start_ollama


def test_release_docs_and_status_match_current_truth() -> None:
    release_doc = (
        REPO_ROOT / "docs" / "operations" / "RELEASE_GOVERNANCE.md"
    ).read_text(encoding="utf-8")
    desktop_readiness_doc = (
        REPO_ROOT / "docs" / "operations" / "DESKTOP_DISTRIBUTION_READINESS.md"
    ).read_text(encoding="utf-8")
    backup_restore_doc = (
        REPO_ROOT / "docs" / "operations" / "BACKUP_RESTORE.md"
    ).read_text(encoding="utf-8")
    rollback_doc = (REPO_ROOT / "docs" / "operations" / "ROLLBACK.md").read_text(
        encoding="utf-8"
    )
    operations_doc = (REPO_ROOT / "docs" / "operations" / "OPERATIONS.md").read_text(
        encoding="utf-8"
    )
    incident_triage = (
        REPO_ROOT / "docs" / "operations" / "INCIDENT_TRIAGE.md"
    ).read_text(encoding="utf-8")
    observability_readme = (
        REPO_ROOT / "ops" / "observability" / "README.md"
    ).read_text(encoding="utf-8")
    project_status = (
        REPO_ROOT / "docs" / "governance" / "PROJECT_STATUS.md"
    ).read_text(encoding="utf-8")
    roadmap_archive = (
        REPO_ROOT / "docs" / "governance" / "ROADMAP_ARCHIVE.md"
    ).read_text(encoding="utf-8")
    security_doc = (REPO_ROOT / "docs" / "governance" / "SECURITY.md").read_text(
        encoding="utf-8"
    )
    object_storage_contract = (
        REPO_ROOT / "docs" / "architecture" / "OBJECT_STORAGE_CONTRACT.md"
    ).read_text(encoding="utf-8")

    assert "`STAGING_BASE_URL`" in release_doc
    assert "`PRODUCTION_BASE_URL`" in release_doc
    assert "immutable bundle" in release_doc
    assert "promotion evidence" in release_doc
    assert "exercise_release_rollback_drill" in rollback_doc
    assert "python -m tools.quality.run_pr_latency_gate" in operations_doc
    assert "`backend-fast`" in operations_doc
    assert "`backend-heavy`" in operations_doc
    assert "OTel enabled-path tests" in operations_doc
    assert "observability asset contract" in operations_doc
    assert "`GOAT_USE_SCHOOL_OLLAMA_LOCAL`" in operations_doc
    assert "Simon school Ubuntu server profile" in operations_doc
    assert "prefers `.env.school-ubuntu`" in operations_doc
    assert "python -m tools.desktop.packaged_shell_fault_smoke" in operations_doc
    assert (
        "python -m tools.desktop.installed_windows_desktop_fault_smoke"
        in operations_doc
    )
    assert "desktop-linux-ci-provenance.json" in operations_doc
    assert "DESKTOP_DISTRIBUTION_READINESS.md" in operations_doc
    assert "`GOAT_OBJECT_STORE_BACKEND`" in operations_doc
    assert "`GOAT_OBJECT_STORE_ROOT`" in operations_doc
    assert "`GOAT_OBJECT_STORE_BUCKET`" in operations_doc
    assert "matching object-store snapshot as one recovery unit" in operations_doc
    assert "desktop-windows-fault-smoke" in operations_doc
    assert "artifact should contain at least" in operations_doc
    assert "installed Windows evidence now writes" in operations_doc
    assert "install -> healthy launch -> fault scenarios -> uninstall" in operations_doc
    assert "GOAT_READY_SKIP_OLLAMA_PROBE=1" in operations_doc
    assert "desktop-installed-smoke/*/summary.json" in operations_doc
    assert "desktop-fault-smoke/summary.json" in incident_triage
    assert "desktop-fault-smoke/build.log" in incident_triage
    assert "healthy_launch" in incident_triage
    assert "desktop-installed-smoke/*/summary.json" in incident_triage
    assert "Linux sidecar/provenance/cargo-audit gate" in operations_doc
    assert "does not own the Windows pre-ready retry semantics" in operations_doc
    assert "`desktop-package-windows`" in incident_triage
    assert "`desktop-supply-chain`" in incident_triage
    assert "`backend-fast`" in incident_triage
    assert "OTel enabled-path tests" in incident_triage
    assert "observability asset contract" in incident_triage
    assert "hang_before_ready" in incident_triage
    assert "installer kind (`msi` vs `nsis`)" in incident_triage
    assert "EXPORTED_METRIC_FAMILIES" in observability_readme
    assert "mechanically verified" in observability_readme
    assert "`desktop-package-windows`" in security_doc
    assert (
        "installed-app startup evidence for both MSI and NSIS artifacts" in security_doc
    )
    assert "`desktop-supply-chain`" in security_doc
    assert "`ops/deploy/deploy.sh`" in operations_doc
    assert "`ops/systemd/goat-ai.service`" in operations_doc
    assert "`ops/systemd/goat-ai.school-ubuntu.service`" in operations_doc
    assert "Simon school Ubuntu server profile" in operations_doc
    assert "<app_log_dir>/desktop-shell.log" in operations_doc
    assert "GOAT_OBJECT_STORE_ROOT" in backup_restore_doc
    assert "bucket/prefix snapshot" in backup_restore_doc
    assert "python -m tools.ops.upgrade_runtime_postgres_schema" in backup_restore_doc
    assert "python -m tools.ops.import_runtime_metadata_snapshot" in backup_restore_doc
    assert "python -m tools.ops.check_runtime_metadata_parity" in backup_restore_doc
    assert "paired SQLite + object-store" in rollback_doc
    assert "python -m tools.ops.upgrade_runtime_postgres_schema" in rollback_doc
    assert "P0, P1, and P2 are complete" not in project_status
    assert "artifact-first staged release governance workflow" in project_status
    assert "backend-fast -> backend-heavy -> backend" in project_status
    assert "desktop-package-windows" in project_status
    assert "installed Windows evidence" in project_status
    assert "DESKTOP_DISTRIBUTION_READINESS.md" in release_doc
    assert "Linux packaged-desktop path" in release_doc
    assert "macOS public distribution remains blocked" in release_doc
    assert "Platform matrix" in desktop_readiness_doc
    assert "macOS public distribution blockers" in desktop_readiness_doc
    assert "Updater readiness gate" in desktop_readiness_doc
    assert "GOAT_RUNTIME_ROOT" in desktop_readiness_doc
    assert "OBJECT_STORAGE_CONTRACT.md" in project_status
    assert "Phase 16C storage closeout" in roadmap_archive
    assert "GOAT_OBJECT_STORE_ROOT" in roadmap_archive
    assert "stable `/api/artifacts/{artifact_id}` contract" in project_status
    assert "stable `/api/artifacts/{artifact_id}` contract" in object_storage_contract


def test_phase16_object_store_docs_match_runtime_contract() -> None:
    operations_doc = (REPO_ROOT / "docs" / "operations" / "OPERATIONS.md").read_text(
        encoding="utf-8"
    )
    backup_doc = (REPO_ROOT / "docs" / "operations" / "BACKUP_RESTORE.md").read_text(
        encoding="utf-8"
    )
    rollback_doc = (REPO_ROOT / "docs" / "operations" / "ROLLBACK.md").read_text(
        encoding="utf-8"
    )
    api_reference = (REPO_ROOT / "docs" / "api" / "API_REFERENCE.md").read_text(
        encoding="utf-8"
    )

    for snippet in (
        "GOAT_OBJECT_STORE_BACKEND",
        "GOAT_OBJECT_STORE_ROOT",
        "GOAT_OBJECT_STORE_BUCKET",
        "GOAT_OBJECT_STORE_PREFIX",
        "object payloads must be captured from `GOAT_OBJECT_STORE_ROOT` or the configured bucket/prefix",
        "matched SQLite + object-store restore set",
        "knowledge upload/ingestion/search on a small test document",
        "persisted through the configured object store using a canonical `storage_key`",
        "persists through the configured object store for the lifetime of the attachment id",
        "Resolves the payload by persisted `storage_key`",
    ):
        assert snippet in (operations_doc + backup_doc + rollback_doc + api_reference)

    assert "GOAT_DATA_DIR/uploads/knowledge" not in api_reference
    assert (
        "persists under `GOAT_DATA_DIR` for the lifetime of the attachment id"
        not in (api_reference)
    )
