from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from goat_ai.config import Settings
from goat_ai.feature_gates import compute_code_sandbox_snapshot, probe_docker_available


def _settings(root: Path, **kwargs: object) -> Settings:
    return Settings(
        ollama_base_url="http://127.0.0.1:11434",
        generate_timeout=120,
        max_upload_mb=20,
        max_upload_bytes=20 * 1024 * 1024,
        max_dataframe_rows=50000,
        use_chat_api=True,
        system_prompt="t",
        app_root=root,
        logo_svg=root / "x.svg",
        log_db_path=root / "db.sqlite",
        **kwargs,
    )


class TestFeatureGates(unittest.TestCase):
    def test_code_sandbox_disabled_by_operator(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            s = _settings(Path(tmp), feature_code_sandbox_enabled=False)
            snap = compute_code_sandbox_snapshot(s)
            self.assertFalse(snap.effective_enabled)
            self.assertEqual("disabled_by_operator", snap.deny_reason)

    @patch("goat_ai.feature_gates._path_usable_for_docker", return_value=True)
    def test_code_sandbox_enabled_when_config_and_probe_ok(self, _mock: object) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            s = _settings(Path(tmp), feature_code_sandbox_enabled=True)
            snap = compute_code_sandbox_snapshot(s)
            self.assertTrue(snap.effective_enabled)
            self.assertIsNone(snap.deny_reason)

    @patch("goat_ai.feature_gates._path_usable_for_docker", return_value=False)
    def test_code_sandbox_docker_unavailable(self, _mock: object) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            s = _settings(Path(tmp), feature_code_sandbox_enabled=True)
            snap = compute_code_sandbox_snapshot(s)
            self.assertFalse(snap.effective_enabled)
            self.assertEqual("docker_unavailable", snap.deny_reason)

    def test_probe_docker_false_for_plain_file_on_unix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bogus = root / "not_a_socket"
            bogus.write_text("x", encoding="utf-8")
            s = _settings(root, feature_code_sandbox_enabled=True, docker_socket_path=str(bogus))
            self.assertFalse(probe_docker_available(s))


if __name__ == "__main__":
    unittest.main()
