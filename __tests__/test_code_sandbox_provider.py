from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from backend.services.code_sandbox_provider import (
    DockerException,
    DockerSandboxProvider,
    LocalHostProvider,
    SandboxProviderRequest,
)
from backend.services.exceptions import FeatureNotAvailable
from goat_ai.config import Settings


def _settings(root: Path) -> Settings:
    return Settings(
        ollama_base_url="http://127.0.0.1:11434",
        generate_timeout=120,
        max_upload_mb=20,
        max_upload_bytes=20 * 1024 * 1024,
        max_dataframe_rows=50000,
        use_chat_api=True,
        system_prompt="t",
        app_root=root,
        logo_svg=root / "logo.svg",
        log_db_path=root / "db.sqlite",
    )


class DockerSandboxProviderTests(unittest.TestCase):
    def test_provider_creates_no_network_limited_container_and_cleans_up(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            settings = _settings(Path(tmp))
            provider = DockerSandboxProvider(settings)

            container = MagicMock()
            container.attrs = {"State": {"Status": "exited", "ExitCode": 0}}
            container.logs.side_effect = [b"ok", b""]
            container.reload.return_value = None

            client = MagicMock()
            client.containers.create.return_value = container

            with patch(
                "backend.services.code_sandbox_provider.docker.DockerClient",
                return_value=client,
            ):
                events = list(
                    provider.run_stream(
                        SandboxProviderRequest(
                            execution_id="cs-1",
                            runtime_preset="shell",
                            code="echo ok",
                            command=None,
                            stdin="hello",
                            inline_files=[],
                            timeout_sec=2,
                            network_policy="disabled",
                        )
                    )
                )
                result = events[-1]

            self.assertEqual("docker", result.provider_name)
            self.assertEqual(0, result.exit_code)
            create_kwargs = client.containers.create.call_args.kwargs
            self.assertTrue(create_kwargs["network_disabled"])
            self.assertEqual("256m", create_kwargs["mem_limit"])
            self.assertEqual(500_000_000, create_kwargs["nano_cpus"])
            container.remove.assert_called_once_with(force=True)

    def test_provider_maps_docker_failures_to_feature_unavailable(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            settings = _settings(Path(tmp))
            provider = DockerSandboxProvider(settings)

            with patch(
                "backend.services.code_sandbox_provider.docker.DockerClient",
                side_effect=DockerException("daemon unavailable"),
            ):
                with self.assertRaises(FeatureNotAvailable) as exc_info:
                    list(
                        provider.run_stream(
                            SandboxProviderRequest(
                                execution_id="cs-1",
                                runtime_preset="shell",
                                code="echo ok",
                                command=None,
                                stdin=None,
                                inline_files=[],
                                timeout_sec=2,
                                network_policy="disabled",
                            )
                        )
                    )
        self.assertEqual("runtime", exc_info.exception.gate_kind)
        self.assertEqual("docker_unavailable", exc_info.exception.deny_reason)


class LocalHostProviderTests(unittest.TestCase):
    def test_provider_executes_on_host_and_collects_outputs(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            settings = _settings(Path(tmp))
            provider = LocalHostProvider(settings)
            if os.name == "nt":
                code = (
                    "Write-Output 'sandbox ok'\n"
                    "New-Item -ItemType Directory -Force -Path outputs | Out-Null\n"
                    "[System.IO.File]::WriteAllText('outputs/report.txt', 'report-ready')\n"
                )
            else:
                code = "printf 'sandbox ok\\n'\nprintf 'report-ready' > outputs/report.txt\n"

            events = list(
                provider.run_stream(
                    SandboxProviderRequest(
                        execution_id="cs-local-1",
                        runtime_preset="shell",
                        code=code,
                        command=None,
                        stdin=None,
                        inline_files=[],
                        timeout_sec=2,
                        network_policy="disabled",
                    )
                )
            )
            result = events[-1]

            self.assertEqual("localhost", result.provider_name)
            self.assertEqual(0, result.exit_code)
            stdout = "".join(
                event.text
                for event in events[:-1]
                if getattr(event, "stream_name", "") == "stdout"
            )
            self.assertIn("sandbox ok", stdout)
            self.assertEqual(1, len(result.output_files))
            self.assertEqual("report.txt", result.output_files[0]["path"])
            self.assertEqual(12, result.output_files[0]["byte_size"])

    @patch(
        "backend.services.code_sandbox_provider._resolve_localhost_shell",
        return_value=None,
    )
    def test_provider_maps_missing_shell_to_feature_unavailable(
        self, _mock: object
    ) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            settings = _settings(Path(tmp))
            provider = LocalHostProvider(settings)

            with self.assertRaises(FeatureNotAvailable) as exc_info:
                list(
                    provider.run_stream(
                        SandboxProviderRequest(
                            execution_id="cs-local-1",
                            runtime_preset="shell",
                            code="echo ok",
                            command=None,
                            stdin=None,
                            inline_files=[],
                            timeout_sec=2,
                            network_policy="disabled",
                        )
                    )
                )
        self.assertEqual("runtime", exc_info.exception.gate_kind)
        self.assertEqual("localhost_unavailable", exc_info.exception.deny_reason)


if __name__ == "__main__":
    unittest.main()
