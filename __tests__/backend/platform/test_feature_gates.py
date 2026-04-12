from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.domain.credential_registry import build_local_authorization_context
from goat_ai.config import Settings
from goat_ai.feature_gates import (
    compute_agent_workbench_snapshot,
    compute_code_sandbox_snapshot,
    probe_docker_available,
    probe_localhost_sandbox_available,
)
from backend.services.feature_gate_service import (
    code_sandbox_policy_allowed,
    require_agent_workbench_enabled,
    require_code_sandbox_enabled,
)
from backend.services.exceptions import FeatureNotAvailable


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

    def test_agent_workbench_disabled_by_operator(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            s = _settings(Path(tmp), feature_agent_workbench_enabled=False)
            snap = compute_agent_workbench_snapshot(s)
            self.assertFalse(snap.effective_enabled)
            self.assertEqual("disabled_by_operator", snap.deny_reason)

    def test_agent_workbench_enabled_opens_runtime_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = _settings(Path(tmp), feature_agent_workbench_enabled=True)
            snap = compute_agent_workbench_snapshot(settings)
            self.assertTrue(snap.allowed_by_config)
            self.assertTrue(snap.available_on_host)
            self.assertTrue(snap.effective_enabled)
            self.assertIsNone(snap.deny_reason)
            require_agent_workbench_enabled(settings)

    @patch("goat_ai.feature_gates._path_usable_for_docker", return_value=True)
    @patch("goat_ai.feature_gates.docker.DockerClient")
    def test_code_sandbox_enabled_when_config_and_probe_ok(
        self, mock_client: object, _mock: object
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mock_client.return_value.ping.return_value = True
            s = _settings(Path(tmp), feature_code_sandbox_enabled=True)
            snap = compute_code_sandbox_snapshot(s)
            self.assertTrue(snap.effective_enabled)
            self.assertIsNone(snap.deny_reason)
            self.assertEqual("docker", snap.provider_name)
            self.assertEqual("container", snap.isolation_level)
            self.assertTrue(snap.network_policy_enforced)

    @patch("goat_ai.feature_gates._path_usable_for_docker", return_value=False)
    def test_code_sandbox_docker_unavailable(self, _mock: object) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            s = _settings(Path(tmp), feature_code_sandbox_enabled=True)
            snap = compute_code_sandbox_snapshot(s)
            self.assertFalse(snap.effective_enabled)
            self.assertEqual("docker_unavailable", snap.deny_reason)

    @patch(
        "goat_ai.feature_gates.resolve_localhost_sandbox_shell",
        return_value="powershell.exe",
    )
    def test_code_sandbox_localhost_enabled_when_shell_available(
        self, _mock: object
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = _settings(
                Path(tmp),
                feature_code_sandbox_enabled=True,
                code_sandbox_provider="localhost",
            )
            snap = compute_code_sandbox_snapshot(settings)
            self.assertTrue(snap.effective_enabled)
            self.assertIsNone(snap.deny_reason)
            self.assertTrue(probe_localhost_sandbox_available(settings))
            self.assertEqual("localhost", snap.provider_name)
            self.assertEqual("host", snap.isolation_level)
            self.assertFalse(snap.network_policy_enforced)

    @patch("goat_ai.feature_gates.resolve_localhost_sandbox_shell", return_value=None)
    def test_code_sandbox_localhost_unavailable(self, _mock: object) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = _settings(
                Path(tmp),
                feature_code_sandbox_enabled=True,
                code_sandbox_provider="localhost",
            )
            snap = compute_code_sandbox_snapshot(settings)
            self.assertFalse(snap.effective_enabled)
            self.assertEqual("localhost_unavailable", snap.deny_reason)

    def test_probe_docker_false_for_plain_file_on_unix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bogus = root / "not_a_socket"
            bogus.write_text("x", encoding="utf-8")
            s = _settings(
                root, feature_code_sandbox_enabled=True, docker_socket_path=str(bogus)
            )
            self.assertFalse(probe_docker_available(s))

    def test_policy_gate_allows_local_context_with_sandbox_scope(self) -> None:
        self.assertTrue(
            code_sandbox_policy_allowed(build_local_authorization_context())
        )

    @patch("goat_ai.feature_gates._path_usable_for_docker", return_value=True)
    @patch("goat_ai.feature_gates.docker.DockerClient")
    def test_require_code_sandbox_enabled_allows_when_policy_and_runtime_allow(
        self, mock_client: object, _mock: object
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mock_client.return_value.ping.return_value = True
            settings = _settings(Path(tmp), feature_code_sandbox_enabled=True)
            require_code_sandbox_enabled(settings, build_local_authorization_context())

    @patch("goat_ai.feature_gates._path_usable_for_docker", return_value=False)
    def test_require_code_sandbox_enabled_raises_runtime_denial_first(
        self, _mock: object
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = _settings(Path(tmp), feature_code_sandbox_enabled=True)
            with self.assertRaises(FeatureNotAvailable) as exc_info:
                require_code_sandbox_enabled(
                    settings, build_local_authorization_context()
                )
        self.assertEqual("runtime", exc_info.exception.gate_kind)
        self.assertEqual("docker_unavailable", exc_info.exception.deny_reason)

    @patch("goat_ai.feature_gates.resolve_localhost_sandbox_shell", return_value=None)
    def test_require_code_sandbox_enabled_raises_localhost_runtime_denial(
        self, _mock: object
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = _settings(
                Path(tmp),
                feature_code_sandbox_enabled=True,
                code_sandbox_provider="localhost",
            )
            with self.assertRaises(FeatureNotAvailable) as exc_info:
                require_code_sandbox_enabled(
                    settings, build_local_authorization_context()
                )
        self.assertEqual("runtime", exc_info.exception.gate_kind)
        self.assertEqual("localhost_unavailable", exc_info.exception.deny_reason)

    @patch("goat_ai.feature_gates._path_usable_for_docker", return_value=True)
    @patch("goat_ai.feature_gates.docker.DockerClient")
    def test_require_code_sandbox_enabled_raises_policy_denial(
        self, mock_client: object, _mock: object
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mock_client.return_value.ping.return_value = True
            settings = _settings(
                Path(tmp),
                feature_code_sandbox_enabled=True,
                api_key="read-key",
            )
            from backend.domain.credential_registry import resolve_authorization_context

            ctx = resolve_authorization_context(
                provided_api_key="read-key",
                settings=settings,
                legacy_owner_id="",
            )
            assert ctx is not None
            with self.assertRaises(FeatureNotAvailable) as exc_info:
                require_code_sandbox_enabled(settings, ctx)
        self.assertEqual("policy", exc_info.exception.gate_kind)
        self.assertEqual("permission_denied", exc_info.exception.deny_reason)

    def test_require_agent_workbench_enabled_raises_when_operator_disabled(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = _settings(Path(tmp), feature_agent_workbench_enabled=False)
            with self.assertRaises(FeatureNotAvailable) as exc_info:
                require_agent_workbench_enabled(settings)
        self.assertEqual("runtime", exc_info.exception.gate_kind)
        self.assertEqual("disabled_by_operator", exc_info.exception.deny_reason)


if __name__ == "__main__":
    unittest.main()
