from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import time
import winreg
from dataclasses import asdict, dataclass
from pathlib import Path

from tools.desktop import packaged_shell_fault_smoke as packaged_smoke

PRODUCT_DISPLAY_NAME = "GOAT AI"
INSTALL_STATE_REG_PATH = r"Software\simonbb\GOAT AI"
UNINSTALL_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"
DESKTOP_EXE_NAME = "goat-ai-desktop.exe"
SIDECAR_EXE_NAME = "goat-backend.exe"
NSIS_UNINSTALLER_NAME = "uninstall.exe"
DEFAULT_INSTALL_TIMEOUT_SEC = 120.0
DEFAULT_UNINSTALL_TIMEOUT_SEC = 90.0
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

UNINSTALL_ROOTS = (
    winreg.HKEY_CURRENT_USER,
    winreg.HKEY_LOCAL_MACHINE,
)


@dataclass(frozen=True)
class DesktopInstallation:
    installer_kind: str
    installer_path: str
    install_root: str
    desktop_exe: str
    sidecar_path: str
    uninstall_command: str | None
    install_log_path: str | None
    install_stdout_path: str
    install_stderr_path: str


@dataclass(frozen=True)
class UninstallResult:
    succeeded: bool
    exit_code: int | None
    command: str | None
    stdout_path: str
    stderr_path: str
    log_path: str | None
    install_root_removed: bool


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="installed-windows-desktop-fault-smoke",
        description=(
            "Silently install a packaged Windows desktop artifact, run fault-injected "
            "startup scenarios against the installed app, then uninstall and clean up."
        ),
    )
    parser.add_argument("--installer", type=Path, required=True)
    parser.add_argument("--installer-kind", choices=("msi", "nsis"), required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument(
        "--scenario",
        action="append",
        choices=sorted(packaged_smoke.SCENARIO_EXPECTED_STAGE),
        dest="scenarios",
    )
    parser.add_argument("--startup-timeout-sec", type=float, default=15.0)
    parser.add_argument("--health-timeout-sec", type=int, default=2)
    parser.add_argument("--restart-limit", type=int, default=1)
    parser.add_argument("--backoff-ms", type=int, default=100)
    parser.add_argument("--hang-sec", type=float, default=5.0)
    parser.add_argument(
        "--install-timeout-sec",
        type=float,
        default=DEFAULT_INSTALL_TIMEOUT_SEC,
    )
    parser.add_argument(
        "--uninstall-timeout-sec",
        type=float,
        default=DEFAULT_UNINSTALL_TIMEOUT_SEC,
    )
    parser.add_argument(
        "--app-identifier",
        default=packaged_smoke.DEFAULT_WINDOWS_APP_IDENTIFIER,
    )
    return parser


def _normalize_path(value: Path | str) -> str:
    return str(Path(value).resolve()).rstrip("\\/")


def _iter_uninstall_entries() -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for hive in UNINSTALL_ROOTS:
        try:
            uninstall_root = winreg.OpenKey(hive, UNINSTALL_REG_PATH)
        except FileNotFoundError:
            continue
        with uninstall_root:
            subkey_count = winreg.QueryInfoKey(uninstall_root)[0]
            for index in range(subkey_count):
                try:
                    subkey_name = winreg.EnumKey(uninstall_root, index)
                    subkey = winreg.OpenKey(uninstall_root, subkey_name)
                except OSError:
                    continue
                with subkey:
                    try:
                        display_name = str(
                            winreg.QueryValueEx(subkey, "DisplayName")[0]
                        )
                    except FileNotFoundError:
                        continue
                    install_location = ""
                    uninstall_string = ""
                    quiet_uninstall_string = ""
                    for value_name, target in (
                        ("InstallLocation", "install_location"),
                        ("UninstallString", "uninstall_string"),
                        ("QuietUninstallString", "quiet_uninstall_string"),
                    ):
                        try:
                            value = str(winreg.QueryValueEx(subkey, value_name)[0])
                        except FileNotFoundError:
                            value = ""
                        if target == "install_location":
                            install_location = value
                        elif target == "uninstall_string":
                            uninstall_string = value
                        else:
                            quiet_uninstall_string = value
                    entries.append(
                        {
                            "display_name": display_name,
                            "install_location": install_location,
                            "uninstall_string": uninstall_string,
                            "quiet_uninstall_string": quiet_uninstall_string,
                        }
                    )
    return entries


def _clear_install_state_registry() -> None:
    def delete_tree(hive: int, subkey_path: str) -> None:
        try:
            key = winreg.OpenKey(
                hive, subkey_path, 0, winreg.KEY_READ | winreg.KEY_WRITE
            )
        except FileNotFoundError:
            return
        with key:
            while True:
                try:
                    child_name = winreg.EnumKey(key, 0)
                except OSError:
                    break
                delete_tree(hive, f"{subkey_path}\\{child_name}")
        winreg.DeleteKey(hive, subkey_path)

    delete_tree(winreg.HKEY_CURRENT_USER, INSTALL_STATE_REG_PATH)


def _run_process(
    *,
    args: list[str],
    cwd: Path | None,
    env: dict[str, str] | None,
    stdout_path: Path,
    stderr_path: Path,
    timeout_sec: float,
) -> int:
    with (
        stdout_path.open("w", encoding="utf-8") as stdout_file,
        stderr_path.open("w", encoding="utf-8") as stderr_file,
    ):
        process = subprocess.Popen(  # noqa: S603
            args,
            cwd=str(cwd) if cwd else None,
            env=env,
            stdout=stdout_file,
            stderr=stderr_file,
            creationflags=CREATE_NO_WINDOW,
        )
        try:
            return int(process.wait(timeout=timeout_sec))
        except subprocess.TimeoutExpired as exc:
            process.kill()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            raise SystemExit(
                f"Command {' '.join(args)!r} did not exit within {timeout_sec} seconds."
            ) from exc


def _discover_installed_file(install_root: Path, file_name: str) -> Path:
    candidates = [path for path in install_root.rglob(file_name) if path.is_file()]
    if not candidates:
        raise SystemExit(
            f"Could not find {file_name} under installed root {install_root}."
        )
    return min(candidates, key=lambda path: len(path.parts))


def _match_uninstall_entry(install_root: Path) -> dict[str, str]:
    normalized_root = _normalize_path(install_root)
    matching_entries = [
        entry
        for entry in _iter_uninstall_entries()
        if entry["display_name"] == PRODUCT_DISPLAY_NAME
    ]
    for entry in matching_entries:
        if entry["display_name"] != PRODUCT_DISPLAY_NAME:
            continue
        install_location = entry["install_location"].strip()
        if install_location and _normalize_path(install_location) == normalized_root:
            return entry
    discovered_roots = sorted(
        {
            entry["install_location"].strip()
            for entry in matching_entries
            if entry["install_location"].strip()
        }
    )
    raise SystemExit(
        f"Could not find Windows uninstall metadata for {PRODUCT_DISPLAY_NAME} at {install_root}. "
        f"Discovered existing install roots: {discovered_roots or ['<none>']}."
    )


def install_desktop_artifact(
    *,
    installer_path: Path,
    installer_kind: str,
    artifact_dir: Path,
    install_timeout_sec: float,
) -> DesktopInstallation:
    install_root = (artifact_dir / "installed-app").resolve()
    if install_root.exists():
        shutil.rmtree(install_root, ignore_errors=True)
    install_root.mkdir(parents=True, exist_ok=True)
    install_stdout_path = artifact_dir / "install.stdout.log"
    install_stderr_path = artifact_dir / "install.stderr.log"

    _clear_install_state_registry()

    if installer_kind == "msi":
        install_log_path = artifact_dir / "install.msiexec.log"
        args = [
            "msiexec.exe",
            "/i",
            str(installer_path),
            "ALLUSERS=2",
            "MSIINSTALLPERUSER=1",
            f"INSTALLDIR={install_root}",
            "/qn",
            "/norestart",
            "/l*v",
            str(install_log_path),
        ]
        exit_code = _run_process(
            args=args,
            cwd=None,
            env=None,
            stdout_path=install_stdout_path,
            stderr_path=install_stderr_path,
            timeout_sec=install_timeout_sec,
        )
        if exit_code != 0:
            raise SystemExit(f"MSI install failed with exit code {exit_code}.")
        uninstall_entry = _match_uninstall_entry(install_root)
        uninstall_command = (
            uninstall_entry["quiet_uninstall_string"]
            or uninstall_entry["uninstall_string"]
        )
    else:
        install_log_path = None
        args = [str(installer_path), "/S", f"/D={install_root}"]
        exit_code = _run_process(
            args=args,
            cwd=installer_path.parent,
            env=None,
            stdout_path=install_stdout_path,
            stderr_path=install_stderr_path,
            timeout_sec=install_timeout_sec,
        )
        if exit_code != 0:
            raise SystemExit(f"NSIS install failed with exit code {exit_code}.")
        uninstall_command = str(
            _discover_installed_file(install_root, NSIS_UNINSTALLER_NAME)
        )

    desktop_exe = _discover_installed_file(install_root, DESKTOP_EXE_NAME)
    sidecar_path = _discover_installed_file(install_root, SIDECAR_EXE_NAME)
    return DesktopInstallation(
        installer_kind=installer_kind,
        installer_path=str(installer_path),
        install_root=str(install_root),
        desktop_exe=str(desktop_exe),
        sidecar_path=str(sidecar_path),
        uninstall_command=uninstall_command,
        install_log_path=str(install_log_path) if install_log_path else None,
        install_stdout_path=str(install_stdout_path),
        install_stderr_path=str(install_stderr_path),
    )


def _msi_uninstall_args(command: str, uninstall_log_path: Path) -> list[str]:
    guid_match = re.search(r"\{[0-9A-Fa-f-]+\}", command)
    if guid_match is None:
        raise SystemExit(
            f"Could not extract MSI product code from uninstall command {command!r}."
        )
    return [
        "msiexec.exe",
        "/x",
        guid_match.group(0),
        "/qn",
        "/norestart",
        "/l*v",
        str(uninstall_log_path),
    ]


def _remove_install_root(install_root: Path) -> bool:
    for _ in range(5):
        if not install_root.exists():
            return True
        shutil.rmtree(install_root, ignore_errors=True)
        if not install_root.exists():
            return True
        time.sleep(1)
    return not install_root.exists()


def uninstall_desktop_artifact(
    *,
    installation: DesktopInstallation,
    artifact_dir: Path,
    uninstall_timeout_sec: float,
) -> UninstallResult:
    uninstall_stdout_path = artifact_dir / "uninstall.stdout.log"
    uninstall_stderr_path = artifact_dir / "uninstall.stderr.log"
    uninstall_log_path: Path | None = None
    exit_code: int | None = None

    if installation.uninstall_command:
        if installation.installer_kind == "msi":
            uninstall_log_path = artifact_dir / "uninstall.msiexec.log"
            args = _msi_uninstall_args(
                installation.uninstall_command, uninstall_log_path
            )
            exit_code = _run_process(
                args=args,
                cwd=None,
                env=None,
                stdout_path=uninstall_stdout_path,
                stderr_path=uninstall_stderr_path,
                timeout_sec=uninstall_timeout_sec,
            )
        else:
            args = [installation.uninstall_command, "/S"]
            exit_code = _run_process(
                args=args,
                cwd=Path(installation.install_root),
                env=None,
                stdout_path=uninstall_stdout_path,
                stderr_path=uninstall_stderr_path,
                timeout_sec=uninstall_timeout_sec,
            )

    install_root_removed = _remove_install_root(Path(installation.install_root))
    _clear_install_state_registry()
    return UninstallResult(
        succeeded=exit_code in (None, 0),
        exit_code=exit_code,
        command=installation.uninstall_command,
        stdout_path=str(uninstall_stdout_path),
        stderr_path=str(uninstall_stderr_path),
        log_path=str(uninstall_log_path) if uninstall_log_path else None,
        install_root_removed=install_root_removed,
    )


def run_installed_fault_smoke(
    *,
    installation: DesktopInstallation,
    artifact_dir: Path,
    scenarios: list[str],
    startup_timeout_sec: float,
    health_timeout_sec: int,
    restart_limit: int,
    backoff_ms: int,
    hang_sec: float,
    app_identifier: str,
) -> list[packaged_smoke.PackagedShellFaultResult]:
    return [
        packaged_smoke.run_fault_scenario(
            desktop_exe=Path(installation.desktop_exe),
            sidecar_path=Path(installation.sidecar_path),
            artifact_dir=artifact_dir / "scenarios",
            scenario=scenario,
            startup_timeout_sec=startup_timeout_sec,
            health_timeout_sec=health_timeout_sec,
            restart_limit=restart_limit,
            backoff_ms=backoff_ms,
            hang_sec=hang_sec,
            app_identifier=app_identifier,
        )
        for scenario in scenarios
    ]


def main() -> None:
    if os.name != "nt":
        raise SystemExit(
            "installed_windows_desktop_fault_smoke only supports Windows hosts."
        )

    args = _build_parser().parse_args()
    installer_path = args.installer.resolve()
    artifact_dir = args.artifact_dir.resolve()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    scenarios = args.scenarios or list(packaged_smoke.SCENARIO_EXPECTED_STAGE)
    installation: DesktopInstallation | None = None
    uninstall_result: UninstallResult | None = None
    try:
        installation = install_desktop_artifact(
            installer_path=installer_path,
            installer_kind=args.installer_kind,
            artifact_dir=artifact_dir,
            install_timeout_sec=args.install_timeout_sec,
        )
        results = run_installed_fault_smoke(
            installation=installation,
            artifact_dir=artifact_dir,
            scenarios=scenarios,
            startup_timeout_sec=args.startup_timeout_sec,
            health_timeout_sec=args.health_timeout_sec,
            restart_limit=args.restart_limit,
            backoff_ms=args.backoff_ms,
            hang_sec=args.hang_sec,
            app_identifier=args.app_identifier,
        )
    finally:
        if installation is not None:
            uninstall_result = uninstall_desktop_artifact(
                installation=installation,
                artifact_dir=artifact_dir,
                uninstall_timeout_sec=args.uninstall_timeout_sec,
            )

    summary = {
        "installation": asdict(installation) if installation else None,
        "results": [asdict(result) for result in results],
        "uninstall": asdict(uninstall_result) if uninstall_result else None,
    }
    (artifact_dir / "summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
