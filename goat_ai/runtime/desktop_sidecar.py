from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import uvicorn


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
