from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import time
from contextlib import contextmanager, nullcontext
from dataclasses import asdict, dataclass
from pathlib import Path

SCENARIO_EXPECTED_STAGE = {
    "missing_sidecar": "backend_spawn_failed",
    "exit_before_ready": "backend_terminated_before_ready",
    "hang_before_ready": "health_wait_timeout",
}

INTERNAL_TEST_FLAG = "GOAT_DESKTOP_INTERNAL_TEST"
INTERNAL_TEST_SCENARIO = "GOAT_DESKTOP_INTERNAL_TEST_SCENARIO"
INTERNAL_TEST_HEALTH_TIMEOUT_SEC = "GOAT_DESKTOP_INTERNAL_TEST_HEALTH_TIMEOUT_SEC"
INTERNAL_TEST_RESTART_LIMIT = "GOAT_DESKTOP_INTERNAL_TEST_PRE_READY_RESTART_LIMIT"
INTERNAL_TEST_BACKOFF_MS = "GOAT_DESKTOP_INTERNAL_TEST_PRE_READY_BACKOFF_MS"
INTERNAL_TEST_HANG_SEC = "GOAT_DESKTOP_INTERNAL_TEST_HANG_SEC"
DEFAULT_WINDOWS_APP_IDENTIFIER = "com.simonbb.goatai"


@dataclass(frozen=True)
class PackagedShellFaultResult:
    scenario: str
    exit_code: int
    failure_stage: str
    log_path: str
    stdout_path: str
    stderr_path: str


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="packaged-shell-fault-smoke",
        description=(
            "Run fault-injected packaged desktop startup scenarios and assert "
            "that pre-ready failures stay fail-closed with bounded retry evidence."
        ),
    )
    parser.add_argument("--desktop-exe", type=Path, required=True)
    parser.add_argument("--sidecar", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument(
        "--scenario",
        action="append",
        choices=sorted(SCENARIO_EXPECTED_STAGE),
        dest="scenarios",
    )
    parser.add_argument("--startup-timeout-sec", type=float, default=15.0)
    parser.add_argument("--health-timeout-sec", type=int, default=2)
    parser.add_argument("--restart-limit", type=int, default=1)
    parser.add_argument("--backoff-ms", type=int, default=100)
    parser.add_argument("--hang-sec", type=float, default=5.0)
    parser.add_argument("--app-identifier", default=DEFAULT_WINDOWS_APP_IDENTIFIER)
    return parser


def _reserve_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def build_fault_smoke_environment(
    *,
    base_dir: Path,
    scenario: str,
    health_timeout_sec: int,
    restart_limit: int,
    backoff_ms: int,
    hang_sec: float,
) -> dict[str, str]:
    runtime_root = base_dir / "runtime-env"
    local_appdata = runtime_root / "LocalAppData"
    roaming_appdata = runtime_root / "RoamingAppData"
    local_appdata.mkdir(parents=True, exist_ok=True)
    roaming_appdata.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["LOCALAPPDATA"] = str(local_appdata)
    env["APPDATA"] = str(roaming_appdata)
    env["GOAT_DESKTOP_BACKEND_HOST"] = "127.0.0.1"
    env["GOAT_DESKTOP_BACKEND_PORT"] = str(_reserve_local_port())
    env[INTERNAL_TEST_FLAG] = "1"
    env[INTERNAL_TEST_SCENARIO] = "" if scenario == "missing_sidecar" else scenario
    env[INTERNAL_TEST_HEALTH_TIMEOUT_SEC] = str(health_timeout_sec)
    env[INTERNAL_TEST_RESTART_LIMIT] = str(restart_limit)
    env[INTERNAL_TEST_BACKOFF_MS] = str(backoff_ms)
    env[INTERNAL_TEST_HANG_SEC] = str(hang_sec)
    return env


def discover_desktop_log(root: Path) -> Path:
    matches = [path for path in root.rglob("desktop-shell.log") if path.is_file()]
    if not matches:
        raise SystemExit(f"Could not find desktop-shell.log under {root}.")
    return max(matches, key=lambda path: path.stat().st_mtime_ns)


def fallback_desktop_log_path(app_identifier: str) -> Path:
    local_appdata = Path(os.environ.get("LOCALAPPDATA", "")).expanduser()
    if not str(local_appdata).strip():
        raise SystemExit(
            "LOCALAPPDATA was not available for packaged-shell fault smoke."
        )
    return local_appdata / app_identifier / "logs" / "desktop-shell.log"


def extract_log_delta(log_path: Path, baseline: bytes) -> bytes:
    current = log_path.read_bytes()
    if baseline and current.startswith(baseline):
        return current[len(baseline) :]
    return current


def validate_fault_smoke_log(*, scenario: str, exit_code: int, log_text: str) -> str:
    if exit_code == 0:
        raise SystemExit(
            f"Scenario {scenario} unexpectedly exited cleanly; expected fail-closed behavior."
        )
    expected_stage = SCENARIO_EXPECTED_STAGE[scenario]
    if expected_stage not in log_text:
        raise SystemExit(
            f"Scenario {scenario} did not record expected failure stage {expected_stage!r}."
        )
    if "Retrying before window reveal after" not in log_text:
        raise SystemExit(
            f"Scenario {scenario} did not record bounded retry/backoff evidence."
        )
    return expected_stage


def _launch_desktop(
    *,
    desktop_exe: Path,
    env: dict[str, str],
    stdout_path: Path,
    stderr_path: Path,
    timeout_sec: float,
) -> int:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with (
        stdout_path.open("w", encoding="utf-8") as stdout_file,
        stderr_path.open("w", encoding="utf-8") as stderr_file,
    ):
        process = subprocess.Popen(  # noqa: S603
            [str(desktop_exe)],
            cwd=str(desktop_exe.parent),
            env=env,
            stdout=stdout_file,
            stderr=stderr_file,
            creationflags=creationflags,
        )
        try:
            returncode = process.wait(timeout=timeout_sec)
        except subprocess.TimeoutExpired as exc:
            process.kill()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            raise SystemExit(
                f"Desktop process did not exit within {timeout_sec} seconds."
            ) from exc
    return int(returncode)


@contextmanager
def _temporarily_move_sidecar(sidecar_path: Path, scenario_dir: Path):
    if not sidecar_path.is_file():
        raise SystemExit(f"Expected packaged sidecar at {sidecar_path}.")
    backup_path = scenario_dir / sidecar_path.name
    sidecar_path.replace(backup_path)
    try:
        yield
    finally:
        if backup_path.exists():
            backup_path.replace(sidecar_path)


def run_fault_scenario(
    *,
    desktop_exe: Path,
    sidecar_path: Path,
    artifact_dir: Path,
    scenario: str,
    startup_timeout_sec: float,
    health_timeout_sec: int,
    restart_limit: int,
    backoff_ms: int,
    hang_sec: float,
    app_identifier: str,
) -> PackagedShellFaultResult:
    scenario_dir = artifact_dir / scenario
    scenario_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = scenario_dir / "desktop.stdout.log"
    stderr_path = scenario_dir / "desktop.stderr.log"
    env = build_fault_smoke_environment(
        base_dir=scenario_dir,
        scenario=scenario,
        health_timeout_sec=health_timeout_sec,
        restart_limit=restart_limit,
        backoff_ms=backoff_ms,
        hang_sec=hang_sec,
    )
    fallback_log = fallback_desktop_log_path(app_identifier)
    baseline_log = fallback_log.read_bytes() if fallback_log.is_file() else b""
    sidecar_context = (
        _temporarily_move_sidecar(sidecar_path, scenario_dir)
        if scenario == "missing_sidecar"
        else nullcontext()
    )

    with sidecar_context:
        exit_code = _launch_desktop(
            desktop_exe=desktop_exe,
            env=env,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            timeout_sec=startup_timeout_sec,
        )

    time.sleep(0.5)
    if any(path.is_file() for path in scenario_dir.rglob("desktop-shell.log")):
        source_log_path = discover_desktop_log(scenario_dir)
        copied_log_path = source_log_path
        log_text = source_log_path.read_text(encoding="utf-8")
    elif fallback_log.is_file():
        copied_log_path = scenario_dir / "desktop-shell.log"
        copied_log_path.write_bytes(extract_log_delta(fallback_log, baseline_log))
        log_text = copied_log_path.read_text(encoding="utf-8", errors="replace")
    else:
        raise SystemExit(
            f"Could not find desktop-shell.log under {scenario_dir} or at {fallback_log}."
        )
    failure_stage = validate_fault_smoke_log(
        scenario=scenario,
        exit_code=exit_code,
        log_text=log_text,
    )
    result = PackagedShellFaultResult(
        scenario=scenario,
        exit_code=exit_code,
        failure_stage=failure_stage,
        log_path=str(copied_log_path),
        stdout_path=str(stdout_path),
        stderr_path=str(stderr_path),
    )
    (scenario_dir / "result.json").write_text(
        json.dumps(asdict(result), indent=2),
        encoding="utf-8",
    )
    return result


def main() -> None:
    args = _build_parser().parse_args()
    desktop_exe = args.desktop_exe.resolve()
    sidecar_path = args.sidecar.resolve()
    artifact_dir = args.artifact_dir.resolve()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    scenarios = args.scenarios or list(SCENARIO_EXPECTED_STAGE)
    results = [
        run_fault_scenario(
            desktop_exe=desktop_exe,
            sidecar_path=sidecar_path,
            artifact_dir=artifact_dir,
            scenario=scenario,
            startup_timeout_sec=args.startup_timeout_sec,
            health_timeout_sec=args.health_timeout_sec,
            restart_limit=args.restart_limit,
            backoff_ms=args.backoff_ms,
            hang_sec=args.hang_sec,
            app_identifier=args.app_identifier,
        )
        for scenario in scenarios
    ]
    summary = {
        "results": [asdict(result) for result in results],
    }
    (artifact_dir / "summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
