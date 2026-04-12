from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import uvicorn

INTERNAL_TEST_FLAG = "GOAT_DESKTOP_INTERNAL_TEST"
INTERNAL_TEST_SCENARIO = "GOAT_DESKTOP_INTERNAL_TEST_SCENARIO"
INTERNAL_TEST_HANG_SEC = "GOAT_DESKTOP_INTERNAL_TEST_HANG_SEC"


def _default_desktop_data_root() -> Path:
    if sys.platform == "win32":
        base = Path(
            os.environ.get("LOCALAPPDATA")
            or os.environ.get("APPDATA")
            or Path.home() / "AppData" / "Local"
        )
        return base / "GOAT AI"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "GOAT AI"
    xdg_data = os.environ.get("XDG_DATA_HOME", "").strip()
    if xdg_data:
        return Path(xdg_data) / "goat-ai"
    return Path.home() / ".local" / "share" / "goat-ai"


def configure_desktop_environment(data_root: Path, port: int) -> Path:
    resolved_root = data_root.resolve()
    resolved_root.mkdir(parents=True, exist_ok=True)
    (resolved_root / "logs").mkdir(parents=True, exist_ok=True)
    (resolved_root / "data").mkdir(parents=True, exist_ok=True)

    os.environ["GOAT_DESKTOP_APP_DATA_DIR"] = str(resolved_root)
    os.environ["GOAT_RUNTIME_ROOT"] = str(resolved_root)
    os.environ["GOAT_LOG_DIR"] = str(resolved_root / "logs")
    os.environ["GOAT_LOG_PATH"] = str(resolved_root / "chat_logs.db")
    os.environ["GOAT_DATA_DIR"] = str(resolved_root / "data")
    os.environ["GOAT_SERVER_PORT"] = str(port)
    os.environ["GOAT_LOCAL_PORT"] = str(port)
    os.environ["GOAT_DEPLOY_TARGET"] = "local"

    return resolved_root


def _internal_test_enabled() -> bool:
    return os.environ.get(INTERNAL_TEST_FLAG, "").strip() == "1"


def _configured_internal_test_scenario() -> str:
    return os.environ.get(INTERNAL_TEST_SCENARIO, "").strip()


def _configured_internal_test_hang_sec() -> float:
    raw = os.environ.get(INTERNAL_TEST_HANG_SEC, "").strip()
    if not raw:
        return 5.0
    try:
        parsed = float(raw)
    except ValueError:
        return 5.0
    return parsed if parsed > 0 else 5.0


def run_internal_test_scenario_if_requested() -> None:
    if not _internal_test_enabled():
        return

    scenario = _configured_internal_test_scenario()
    if not scenario:
        return
    if scenario == "exit_before_ready":
        raise SystemExit("GOAT desktop internal test: exit_before_ready")
    if scenario == "hang_before_ready":
        time.sleep(_configured_internal_test_hang_sec())
        raise SystemExit("GOAT desktop internal test: hang_before_ready")
    raise SystemExit(f"Unsupported GOAT_DESKTOP_INTERNAL_TEST_SCENARIO: {scenario!r}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="goat-desktop-sidecar",
        description="Launch the bundled GOAT AI FastAPI backend for the desktop shell.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=62606)
    parser.add_argument("--data-root", default="")
    parser.add_argument("--log-level", default="info")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    data_root = (
        Path(args.data_root).expanduser()
        if args.data_root
        else _default_desktop_data_root()
    )
    configure_desktop_environment(data_root, args.port)
    run_internal_test_scenario_if_requested()

    uvicorn.run(
        "backend.main:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        log_level=args.log_level,
        access_log=True,
    )


if __name__ == "__main__":
    main()
