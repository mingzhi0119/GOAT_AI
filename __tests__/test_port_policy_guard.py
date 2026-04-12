from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

SUPPORTED_PORT_POLICY_FILES = [
    REPO_ROOT / "backend" / "config.py",
    REPO_ROOT / "server.py",
    REPO_ROOT / "frontend" / "vite.config.ts",
    REPO_ROOT / ".env.example",
    REPO_ROOT / "goat_ai" / "runtime_target.py",
    REPO_ROOT / "scripts" / "post_deploy_check.py",
    REPO_ROOT / "docs" / "OPERATIONS.md",
]


def test_supported_port_policy_files_reference_single_runtime_port() -> None:
    for path in SUPPORTED_PORT_POLICY_FILES:
        text = path.read_text(encoding="utf-8")
        assert "62606" in text, f"{path} should document the single runtime port"
        assert "8001" not in text, f"{path} should not reference deprecated port 8001"
        if path.name == "OPERATIONS.md":
            assert "no `8002` fallback" in text
        else:
            assert "8002" not in text, (
                f"{path} should not reference deprecated port 8002"
            )
