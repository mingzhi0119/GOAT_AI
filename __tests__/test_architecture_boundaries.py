from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _python_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.py")
        if "__pycache__" not in path.parts
    )


def _ts_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.ts") if "node_modules" not in path.parts)


def _tsx_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.tsx") if "node_modules" not in path.parts)


def test_backend_services_do_not_import_fastapi() -> None:
    services_dir = REPO_ROOT / "backend" / "services"
    offenders: list[str] = []
    for path in _python_files(services_dir):
        text = _read_text(path)
        if "from fastapi import" in text or "import fastapi" in text:
            offenders.append(str(path.relative_to(REPO_ROOT)))

    assert not offenders, f"backend/services must not import fastapi directly: {offenders}"


def test_goat_ai_shared_layer_does_not_import_fastapi() -> None:
    shared_dir = REPO_ROOT / "goat_ai"
    offenders: list[str] = []
    for path in _python_files(shared_dir):
        text = _read_text(path)
        if "from fastapi import" in text or "import fastapi" in text:
            offenders.append(str(path.relative_to(REPO_ROOT)))

    assert not offenders, f"goat_ai shared layer must not import fastapi: {offenders}"


def test_backend_routers_avoid_direct_infra_libraries() -> None:
    routers_dir = REPO_ROOT / "backend" / "routers"
    offenders: list[str] = []
    banned_markers = ("import sqlite3", "from sqlite3", "import requests", "from requests")
    for path in _python_files(routers_dir):
        text = _read_text(path)
        if any(marker in text for marker in banned_markers):
            offenders.append(str(path.relative_to(REPO_ROOT)))

    assert not offenders, f"backend/routers should not directly import infrastructure libs: {offenders}"


def test_frontend_hooks_do_not_import_components() -> None:
    hooks_dir = REPO_ROOT / "frontend" / "src" / "hooks"
    offenders: list[str] = []
    component_markers = (
        "from '../components/",
        'from "../components/',
        "from './components/",
        'from "./components/',
        "from '@/components/",
        'from "@/components/',
    )

    for path in [*_ts_files(hooks_dir), *_tsx_files(hooks_dir)]:
        text = _read_text(path)
        if any(marker in text for marker in component_markers):
            offenders.append(str(path.relative_to(REPO_ROOT)))

    assert not offenders, f"frontend hooks must not import from components: {offenders}"
