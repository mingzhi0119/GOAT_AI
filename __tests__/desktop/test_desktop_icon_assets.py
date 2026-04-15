from __future__ import annotations

from pathlib import Path

from __tests__.helpers.repo_root import repo_root


REPO_ROOT = repo_root(Path(__file__))


def test_desktop_bundle_uses_capricorn_icon_and_removed_goat_asset() -> None:
    frontend_root = REPO_ROOT / "frontend"
    tauri_root = frontend_root / "src-tauri"
    icon_dir = tauri_root / "icons"

    assert not (frontend_root / "public" / "golden_goat_icon.png").exists()
    assert not (REPO_ROOT / "static" / "golden_goat_icon.png").exists()
    assert (icon_dir / "icon.svg").is_file()
    assert (icon_dir / "icon.png").is_file()
    assert (icon_dir / "icon.ico").is_file()

    tauri_config = (tauri_root / "tauri.conf.json").read_text(encoding="utf-8")
    assert '"icon": ["icons/icon.ico", "icons/icon.png"]' in tauri_config

    goat_icon = (frontend_root / "src" / "components" / "GoatIcon.tsx").read_text(
        encoding="utf-8"
    )
    assert "ZodiacCapricorn" in goat_icon
