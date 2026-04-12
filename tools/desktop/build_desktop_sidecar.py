from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_ROOT = REPO_ROOT / "frontend"
TAURI_ROOT = FRONTEND_ROOT / "src-tauri"
BINARIES_DIR = TAURI_ROOT / "binaries"
BUILD_ROOT = TAURI_ROOT / ".desktop-sidecar-build"
ENTRYPOINT = REPO_ROOT / "goat_ai" / "runtime" / "desktop_sidecar.py"
BASE_NAME = "goat-backend"


def _find_rustc() -> Path | None:
    rustc = shutil.which("rustc")
    if rustc:
        return Path(rustc)
    cargo_home = (
        Path.home()
        / ".cargo"
        / "bin"
        / ("rustc.exe" if sys.platform == "win32" else "rustc")
    )
    return cargo_home if cargo_home.is_file() else None


def _detect_target_triple() -> str:
    rustc = _find_rustc()
    if rustc is None:
        raise SystemExit(
            "Could not find rustc. Install the desktop prerequisites first "
            "(see scripts/desktop/install_desktop_prereqs.ps1 -Profile Dev)."
        )
    completed = subprocess.run(
        [str(rustc), "--print", "host-tuple"],
        check=True,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    triple = completed.stdout.strip()
    if not triple:
        raise SystemExit("rustc did not return a host target triple.")
    return triple


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the packaged GOAT AI desktop backend sidecar with PyInstaller."
    )
    parser.add_argument("--target-triple", default="")
    parser.add_argument("--clean", action="store_true")
    return parser


def _add_data_arg(source: Path, target: str) -> str:
    separator = ";" if sys.platform == "win32" else ":"
    return f"{source}{separator}{target}"


def main() -> None:
    args = _build_parser().parse_args()
    target_triple = args.target_triple.strip() or _detect_target_triple()
    extension = ".exe" if sys.platform == "win32" else ""
    output_name = f"{BASE_NAME}-{target_triple}{extension}"
    tmp_name = f"{BASE_NAME}-build"
    dist_dir = BUILD_ROOT / "dist"
    work_dir = BUILD_ROOT / "work"
    spec_dir = BUILD_ROOT / "spec"

    if args.clean and BUILD_ROOT.exists():
        shutil.rmtree(BUILD_ROOT)

    BINARIES_DIR.mkdir(parents=True, exist_ok=True)
    dist_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)
    spec_dir.mkdir(parents=True, exist_ok=True)

    pyinstaller_command = [
        sys.executable,
        "-m",
        "PyInstaller.__main__",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        tmp_name,
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(work_dir),
        "--specpath",
        str(spec_dir),
        "--add-data",
        _add_data_arg(REPO_ROOT / "backend" / "migrations", "backend/migrations"),
        str(ENTRYPOINT),
    ]

    try:
        subprocess.run(pyinstaller_command, check=True, cwd=str(REPO_ROOT))
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            "PyInstaller build failed. Install desktop build dependencies with "
            "`pip install -r requirements-desktop-build.txt` and retry."
        ) from exc

    built_binary = dist_dir / f"{tmp_name}{extension}"
    if not built_binary.is_file():
        raise SystemExit(
            f"Expected PyInstaller output at {built_binary}, but it was not created."
        )

    final_binary = BINARIES_DIR / output_name
    replacement_binary = BINARIES_DIR / f"{output_name}.tmp"
    if replacement_binary.exists():
        replacement_binary.unlink()
    shutil.copy2(built_binary, replacement_binary)
    try:
        replacement_binary.replace(final_binary)
    except PermissionError as exc:
        replacement_binary.unlink(missing_ok=True)
        raise SystemExit(
            f"Could not replace the packaged desktop sidecar at {final_binary}. "
            "Close any running desktop app or process that is locking the binary and retry."
        ) from exc
    print(final_binary)


if __name__ == "__main__":
    main()
