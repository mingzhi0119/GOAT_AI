from __future__ import annotations

import json
from pathlib import Path

import pytest

import tools.desktop.installed_windows_desktop_fault_smoke as subject
from tools.desktop import packaged_shell_fault_smoke as packaged_smoke


def test_registry_helpers_degrade_gracefully_without_winreg(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(subject, "winreg", None)
    monkeypatch.setattr(subject, "UNINSTALL_ROOTS", ())

    assert subject._iter_uninstall_entries() == []
    subject._clear_install_state_registry()


def test_match_uninstall_entry_uses_install_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    install_root = tmp_path / "installed-app"
    install_root.mkdir()
    monkeypatch.setattr(
        subject,
        "_iter_uninstall_entries",
        lambda: [
            {
                "display_name": "GOAT AI",
                "install_location": f"{install_root}\\",
                "uninstall_string": "MsiExec.exe /X{ABC}",
                "quiet_uninstall_string": "",
            }
        ],
    )

    entry = subject._match_uninstall_entry(install_root)

    assert entry["uninstall_string"] == "MsiExec.exe /X{ABC}"


def test_install_desktop_artifact_builds_nsis_silent_install(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    installer = tmp_path / "setup.exe"
    installer.write_text("", encoding="utf-8")
    artifact_dir = tmp_path / "artifacts"
    captured: dict[str, object] = {}

    monkeypatch.setattr(subject, "_clear_install_state_registry", lambda: None)

    def fake_run_process(**kwargs: object) -> int:
        captured["args"] = kwargs["args"]
        captured["cwd"] = kwargs["cwd"]
        return 0

    monkeypatch.setattr(subject, "_run_process", fake_run_process)
    monkeypatch.setattr(
        subject,
        "_discover_installed_file",
        lambda install_root, file_name: install_root / file_name,
    )

    installation = subject.install_desktop_artifact(
        installer_path=installer,
        installer_kind="nsis",
        artifact_dir=artifact_dir,
        install_timeout_sec=30,
    )

    assert captured["cwd"] == installer.parent
    assert captured["args"] == [
        str(installer),
        "/S",
        f"/D={Path(installation.install_root)}",
    ]
    assert installation.uninstall_command.endswith("uninstall.exe")


def test_msi_uninstall_args_extract_product_code() -> None:
    uninstall_log = Path("uninstall.msiexec.log")

    args = subject._msi_uninstall_args(
        "MsiExec.exe /X{52B5624C-FF4C-45F1-8FCC-040618AD94CD}",
        uninstall_log,
    )

    assert args[:5] == [
        "msiexec.exe",
        "/x",
        "{52B5624C-FF4C-45F1-8FCC-040618AD94CD}",
        "/qn",
        "/norestart",
    ]
    assert args[-2:] == ["/l*v", str(uninstall_log)]


def test_main_writes_summary_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    artifact_dir = tmp_path / "artifacts"
    installer = tmp_path / "setup.exe"
    installer.write_text("", encoding="utf-8")
    installation = subject.DesktopInstallation(
        installer_kind="nsis",
        installer_path=str(installer),
        install_root=str(tmp_path / "install-root"),
        desktop_exe=str(tmp_path / "install-root" / "goat-ai-desktop.exe"),
        sidecar_path=str(tmp_path / "install-root" / "goat-backend.exe"),
        uninstall_command=str(tmp_path / "install-root" / "uninstall.exe"),
        install_log_path=None,
        install_stdout_path="install.stdout.log",
        install_stderr_path="install.stderr.log",
    )
    monkeypatch.setattr(
        subject,
        "_build_parser",
        lambda: _parser_with_namespace(
            installer=installer,
            installer_kind="nsis",
            artifact_dir=artifact_dir,
            scenarios=["missing_sidecar"],
            startup_timeout_sec=15.0,
            health_timeout_sec=2,
            restart_limit=1,
            backoff_ms=100,
            hang_sec=5.0,
            install_timeout_sec=30.0,
            uninstall_timeout_sec=30.0,
            app_identifier=packaged_smoke.DEFAULT_WINDOWS_APP_IDENTIFIER,
            workflow_role="release_evidence",
            release_ref="refs/tags/v1.2.0",
            resolved_sha="abc123",
            distribution_channel="public",
        ),
    )
    monkeypatch.setattr(subject, "install_desktop_artifact", lambda **_: installation)
    monkeypatch.setattr(
        subject,
        "run_installed_fault_smoke",
        lambda **_: [
            packaged_smoke.PackagedShellFaultResult(
                scenario="missing_sidecar",
                exit_code=1,
                failure_stage="backend_spawn_failed",
                log_path="desktop-shell.log",
                stdout_path="stdout.log",
                stderr_path="stderr.log",
            )
        ],
    )
    monkeypatch.setattr(
        subject,
        "uninstall_desktop_artifact",
        lambda **_: subject.UninstallResult(
            succeeded=True,
            exit_code=0,
            command="uninstall.exe /S",
            stdout_path="uninstall.stdout.log",
            stderr_path="uninstall.stderr.log",
            log_path=None,
            install_root_removed=True,
        ),
    )
    monkeypatch.setattr(subject.os, "name", "nt", raising=False)

    subject.main()

    summary = json.loads((artifact_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "passed"
    assert summary["phase"] == "completed"
    assert summary["installation"]["installer_kind"] == "nsis"
    assert summary["installer_kind"] == "nsis"
    assert summary["workflow_context"]["workflow_role"] == "release_evidence"
    assert summary["workflow_context"]["resolved_sha"] == "abc123"
    assert summary["results"][0]["failure_stage"] == "backend_spawn_failed"
    assert summary["uninstall"]["succeeded"] is True


def test_main_writes_failed_summary_json_when_install_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    artifact_dir = tmp_path / "artifacts"
    installer = tmp_path / "setup.exe"
    installer.write_text("installer", encoding="utf-8")
    monkeypatch.setattr(
        subject,
        "_build_parser",
        lambda: _parser_with_namespace(
            installer=installer,
            installer_kind="nsis",
            artifact_dir=artifact_dir,
            scenarios=["missing_sidecar"],
            startup_timeout_sec=15.0,
            health_timeout_sec=2,
            restart_limit=1,
            backoff_ms=100,
            hang_sec=5.0,
            install_timeout_sec=30.0,
            uninstall_timeout_sec=30.0,
            app_identifier=packaged_smoke.DEFAULT_WINDOWS_APP_IDENTIFIER,
            workflow_role="fault_injection_drill",
            release_ref="main",
            resolved_sha="def456",
            distribution_channel="internal_test",
        ),
    )
    monkeypatch.setattr(
        subject,
        "install_desktop_artifact",
        lambda **_: (_ for _ in ()).throw(
            SystemExit("NSIS install failed with exit code 1.")
        ),
    )
    monkeypatch.setattr(subject.os, "name", "nt", raising=False)

    with pytest.raises(SystemExit, match="NSIS install failed"):
        subject.main()

    summary = json.loads((artifact_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "failed"
    assert summary["phase"] == "install"
    assert summary["error"] == "NSIS install failed with exit code 1."
    assert summary["results"] == []
    assert summary["uninstall"] is None
    assert summary["installer_sha256"]


def test_main_rejects_non_windows_hosts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    installer = tmp_path / "setup.exe"
    installer.write_text("", encoding="utf-8")
    artifact_dir = tmp_path / "artifacts"
    monkeypatch.setattr(
        subject,
        "_build_parser",
        lambda: _parser_with_namespace(
            installer=installer,
            installer_kind="nsis",
            artifact_dir=artifact_dir,
            scenarios=["missing_sidecar"],
            startup_timeout_sec=15.0,
            health_timeout_sec=2,
            restart_limit=1,
            backoff_ms=100,
            hang_sec=5.0,
            install_timeout_sec=30.0,
            uninstall_timeout_sec=30.0,
            app_identifier=packaged_smoke.DEFAULT_WINDOWS_APP_IDENTIFIER,
            workflow_role="release_evidence",
            release_ref="refs/tags/v1.2.0",
            resolved_sha="abc123",
            distribution_channel="public",
        ),
    )
    monkeypatch.setattr(subject.os, "name", "posix", raising=False)

    with pytest.raises(SystemExit, match="only supports Windows hosts"):
        subject.main()


def _parser_with_namespace(**kwargs: object):
    parser = subject.argparse.ArgumentParser()
    namespace = type("Args", (), kwargs)()
    parser.parse_args = lambda: namespace  # type: ignore[method-assign]
    return parser
